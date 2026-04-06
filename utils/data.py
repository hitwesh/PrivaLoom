"""
Data preprocessing utilities for PrivaLoom.

Provides enhanced dataset loading, validation, and preprocessing functions
for client dataset handling. Maintains backward compatibility with existing
data loading patterns.
"""

import os
from typing import Optional
from utils.types import TextSample, TextDataset


def load_text_file(file_path: str, encoding: str = "utf-8") -> TextDataset:
    """
    Load text file and return non-empty lines.

    Compatible with existing load_dataset() function behavior.
    Returns empty list if file doesn't exist or can't be read.

    Args:
        file_path: Path to text file
        encoding: File encoding

    Returns:
        List of non-empty text lines
    """
    if not os.path.exists(file_path):
        return []

    try:
        with open(file_path, 'r', encoding=encoding) as handle:
            return [line.strip() for line in handle if line.strip()]
    except (IOError, OSError, UnicodeDecodeError):
        # Return empty list on any file reading error
        return []


def validate_text_samples(samples: TextDataset, min_length: int = 1, max_length: int = 1000) -> TextDataset:
    """
    Validate and filter text samples by length.

    Args:
        samples: List of text samples
        min_length: Minimum sample length in characters
        max_length: Maximum sample length in characters

    Returns:
        Filtered list of valid samples
    """
    valid_samples = []
    for sample in samples:
        if isinstance(sample, str) and min_length <= len(sample) <= max_length:
            valid_samples.append(sample)
    return valid_samples


def preprocess_text(text: str, strip: bool = True, normalize_whitespace: bool = True) -> str:
    """
    Basic text preprocessing.

    Args:
        text: Input text
        strip: Remove leading/trailing whitespace
        normalize_whitespace: Replace multiple whitespace with single space

    Returns:
        Preprocessed text
    """
    if not isinstance(text, str):
        return ""

    result = text
    if strip:
        result = result.strip()

    if normalize_whitespace:
        # Replace multiple whitespace characters with single space
        result = ' '.join(result.split())

    return result


def get_dataset_stats(samples: TextDataset) -> dict[str, int | float]:
    """
    Calculate basic statistics for a text dataset.

    Args:
        samples: List of text samples

    Returns:
        Dictionary with dataset statistics
    """
    if not samples:
        return {
            "total_samples": 0,
            "total_characters": 0,
            "avg_length": 0.0,
            "min_length": 0,
            "max_length": 0
        }

    lengths = [len(sample) for sample in samples]
    return {
        "total_samples": len(samples),
        "total_characters": sum(lengths),
        "avg_length": sum(lengths) / len(lengths),
        "min_length": min(lengths),
        "max_length": max(lengths)
    }