"""Reconstruct multi-turn customer-brand conversation threads from raw tweets."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
from tqdm import tqdm

from src.common.config import DATA_RAW_DIR, DATA_PROCESSED_DIR
from src.common.schemas import Conversation, MessageTurn, SupportCase
from src.data.clean import clean_tweet_text, is_valid_customer_query


def reconstruct_brand_conversations(
    parquet_path: Path = DATA_RAW_DIR / "twcs.parquet",
    target_brand: str = "AppleSupport",
    max_conversations: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Reconstruct complete multi-turn conversation threads for a specific brand.

    Args:
        parquet_path: Path to twcs.parquet dataset.
        target_brand: The brand to filter and reconstruct threads for.
        max_conversations: Optional limit for testing/sampling.

    Returns:
        List of structured conversation dictionaries.
    """
    parquet_path = Path(parquet_path)
    print(f"[Reconstruct] Loading raw dataset for brand '{target_brand}' from {parquet_path}...")
    df = pd.read_parquet(parquet_path)

    # 1. Filter to brand replies and tweets involving this brand
    brand_mask = df["author_id"] == target_brand
    brand_replies = df[brand_mask & df["in_response_to_tweet_id"].notnull()]
    print(f"[Reconstruct] Found {len(brand_replies):,} outbound replies from {target_brand}.")

    # Fast indexed lookup dictionaries
    # Map tweet_id -> row dict
    print("[Reconstruct] Building fast in-memory tweet index...")
    
    # We only need tweets relevant to target_brand to save memory
    # Relevant tweet IDs:
    # 1. All brand tweets
    # 2. All tweets that brand replies to
    # 3. All tweets where text mentions @target_brand
    brand_reply_ids = set(brand_replies["tweet_id"].values)
    parent_ids = set(brand_replies["in_response_to_tweet_id"].dropna().values)
    
    mention_mask = df["text"].str.contains(f"@{target_brand}", case=False, na=False)
    relevant_df = df[brand_mask | df["tweet_id"].isin(parent_ids) | mention_mask].copy()
    
    print(f"[Reconstruct] Filtered to {len(relevant_df):,} relevant candidate tweets.")
    tweet_dict = relevant_df.set_index("tweet_id").to_dict(orient="index")

    # 2. Group by root conversation
    # Trace each brand reply back to root customer tweet
    conversations_map: Dict[str, Dict[str, Any]] = {}

    print("[Reconstruct] Tracing conversation threads...")
    for reply_id in tqdm(brand_reply_ids, desc="Reconstructing threads"):
        current_id = reply_id
        visited = []
        
        # Walk up parent chain to find root
        while current_id in tweet_dict and current_id not in visited:
            visited.append(current_id)
            parent_id = tweet_dict[current_id].get("in_response_to_tweet_id")
            if pd.isna(parent_id) or str(parent_id) not in tweet_dict or str(parent_id) == str(current_id):
                break
            current_id = str(parent_id)

        root_id = visited[-1]
        root_tweet = tweet_dict.get(root_id)
        if not root_tweet:
            continue

        # Root should ideally be an inbound customer tweet
        if not root_tweet.get("inbound", False):
            # If root is brand tweet, skip or take first customer turn
            continue

        root_text = str(root_tweet.get("text", ""))
        if not is_valid_customer_query(root_text, min_words=4):
            continue

        if root_id not in conversations_map:
            conversations_map[root_id] = {
                "root_id": root_id,
                "root_tweet": root_tweet,
                "turns": [],
            }

        # Collect turns in this chain
        conversations_map[root_id]["turns"].extend(visited)

        if max_conversations and len(conversations_map) >= max_conversations:
            break

    print(f"[Reconstruct] Reconstructed {len(conversations_map):,} unique root conversation threads.")

    # 3. Build structured conversation objects
    structured_conversations = []
    for root_id, cdata in conversations_map.items():
        root_tweet = cdata["root_tweet"]
        all_tweet_ids = list(dict.fromkeys(reversed(cdata["turns"])))  # preserve order & deduplicate

        # Chronological sort of turns
        turns_data = []
        for tid in all_tweet_ids:
            if tid in tweet_dict:
                t = tweet_dict[tid]
                role = "customer" if t.get("inbound", False) else "brand"
                turns_data.append({
                    "tweet_id": str(tid),
                    "author_id": str(t.get("author_id", "")),
                    "role": role,
                    "text": str(t.get("text", "")),
                    "cleaned_text": clean_tweet_text(str(t.get("text", ""))),
                    "timestamp": str(t.get("created_at", "")),
                })

        customer_msgs = [t["cleaned_text"] for t in turns_data if t["role"] == "customer"]
        brand_msgs = [t["cleaned_text"] for t in turns_data if t["role"] == "brand"]

        if not customer_msgs or not brand_msgs:
            continue

        initial_problem = customer_msgs[0]
        # Final resolution is the last substantive brand response
        resolution = brand_msgs[-1]

        conv_record = {
            "conversation_id": root_id,
            "brand": target_brand,
            "customer_author_id": str(root_tweet.get("author_id", "")),
            "initial_customer_problem": initial_problem,
            "raw_customer_problem": str(root_tweet.get("text", "")),
            "customer_messages": customer_msgs,
            "brand_messages": brand_msgs,
            "turn_count": len(turns_data),
            "start_time": turns_data[0]["timestamp"],
            "end_time": turns_data[-1]["timestamp"],
            "resolution": resolution,
            "full_thread": turns_data,
        }
        structured_conversations.append(conv_record)

    print(f"[Reconstruct] Final validated conversation count: {len(structured_conversations):,}")
    return structured_conversations
