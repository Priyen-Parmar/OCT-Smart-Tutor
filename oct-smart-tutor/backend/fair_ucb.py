"""
Fair UCB (Upper Confidence Bound) Algorithm for OCT Smart Tutor.

This module implements the Fair UCB algorithm that serves as the
"Curriculum Director" — adaptively selecting which OCT class to present
to each doctor based on their historical performance.

The algorithm:
1. Calculates UCB scores for each class based on the doctor's weakness
2. Classes with lower accuracy get higher UCB scores (more selection weight)
3. A 10% fairness probability ensures even mastered classes appear occasionally
"""
import math
import random
from typing import Optional


CLASS_NAMES = ["CNV", "DME", "DRUSEN", "NORMAL"]


def compute_ucb_scores(stats: dict, total_rounds: int, 
                       exploration_weight: float = 2.0) -> dict:
    """
    Compute Fair UCB scores for each class.
    
    Higher score = doctor is weaker at this class = should be selected more.
    
    Args:
        stats: Dict of {class_name: {"total": int, "correct": int, "accuracy": float}}
        total_rounds: Total number of attempts across all classes
        exploration_weight: Controls exploration vs exploitation (default 2.0)
    
    Returns:
        Dict of {class_name: ucb_score}
    """
    scores = {}
    
    for cls in CLASS_NAMES:
        cls_stats = stats.get(cls, {"total": 0, "correct": 0, "accuracy": 0.0})
        n_i = cls_stats["total"]
        accuracy = cls_stats["accuracy"]
        
        if n_i == 0:
            # Never attempted — highest priority (infinite UCB score)
            scores[cls] = float('inf')
        else:
            # UCB score = (1 - accuracy) + exploration_weight * sqrt(ln(total) / n_i)
            # (1 - accuracy) is the "loss" — higher loss = weaker class
            loss = 1.0 - accuracy
            exploration_bonus = exploration_weight * math.sqrt(
                math.log(total_rounds + 1) / n_i
            )
            scores[cls] = loss + exploration_bonus
    
    return scores


def select_class(stats: dict, fairness_prob: float = 0.10) -> str:
    """
    Select the next class to present using Fair UCB with fairness guarantee.
    
    With probability `fairness_prob`, a random class is selected uniformly
    (to prevent forgetting of mastered classes). Otherwise, the class with
    the highest UCB score is selected.
    
    Args:
        stats: Dict of {class_name: {"total": int, "correct": int, "accuracy": float}}
        fairness_prob: Probability of random selection (default 0.10 = 10%)
    
    Returns:
        Selected class name string
    """
    # Fairness mechanism: 10% chance of random selection
    if random.random() < fairness_prob:
        return random.choice(CLASS_NAMES)
    
    # Calculate total rounds across all classes
    total_rounds = sum(
        stats.get(cls, {}).get("total", 0) for cls in CLASS_NAMES
    )
    
    # If no rounds yet, random selection
    if total_rounds == 0:
        return random.choice(CLASS_NAMES)
    
    # Compute UCB scores
    ucb_scores = compute_ucb_scores(stats, total_rounds)
    
    # Select the class with the highest UCB score
    # If multiple classes have inf score, randomly pick among them
    max_score = max(ucb_scores.values())
    candidates = [cls for cls, score in ucb_scores.items() if score == max_score]
    
    return random.choice(candidates)


def select_image(selected_class: str, image_catalog: dict, 
                 recent_image_ids: Optional[list] = None) -> Optional[dict]:
    """
    Select a random image from the chosen class, avoiding recent images.
    
    Args:
        selected_class: The class chosen by the UCB algorithm
        image_catalog: Dict of {class_name: [list of image info dicts]}
        recent_image_ids: List of recently shown image IDs to avoid repetition
    
    Returns:
        Image info dict or None if no images available
    """
    if selected_class not in image_catalog:
        return None
    
    available = image_catalog[selected_class]
    
    if recent_image_ids:
        # Filter out recently shown images
        filtered = [img for img in available if img["id"] not in recent_image_ids]
        if filtered:
            available = filtered
    
    if not available:
        return None
    
    return random.choice(available)
