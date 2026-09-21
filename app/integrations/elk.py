import pandas as pd
import re
from typing import List, Optional
from pathlib import Path

class ELK:
    """
    Integration class for ELK (Elasticsearch, Logstash, Kibana) traces.
    Currently loads dummy data from an Excel file and performs keyword-based search.
    """
    def __init__(self, file_path: str = "ELK Dumps.xlsx"):
        self.file_path = file_path
        self.df = self._load_data()

    def _load_data(self) -> pd.DataFrame:
        """Loads the ELK dump file into a pandas DataFrame."""
        try:
            return pd.read_excel(self.file_path)
        except Exception as e:
            print(f"Error loading ELK dump file {self.file_path}: {e}")
            return pd.DataFrame()

    def search_trace(self, keywords: List[str]) -> Optional[str]:
        """
        Searches for the single most relevant ELK trace based on keyword matches.

        Args:
            keywords: A list of keywords to search for.

        Returns:
            A formatted string of the best match, or None if no matches are found.
        """
        if self.df.empty or not keywords:
            return None

        # Work on a copy to avoid modifying the original dataframe's state
        # and to avoid SettingWithCopy warnings if df was a slice.
        temp_df = self.df.copy()
        temp_df['match_score'] = 0

        # Search across all columns
        for keyword in keywords:
            # Escape keyword for regex and search case-insensitively
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            for col in temp_df.columns:
                if col == 'match_score':
                    continue
                # Ensure column is treated as string
                temp_df[col] = temp_df[col].astype(str)
                temp_df['match_score'] += temp_df[col].str.count(pattern)

        # Find the row with the maximum score
        max_score = temp_df['match_score'].max()

        # If max_score is NaN (empty series) or 0 (no matches), return None
        if pd.isna(max_score) or max_score == 0:
            return None

        # Get the index of the row with the highest score
        best_match_idx = temp_df['match_score'].idxmax()
        best_match = temp_df.loc[best_match_idx]

        # Remove the internal match_score from the returned record
        result_record = best_match.drop('match_score')

        return self._format_trace(result_record, int(max_score))

    def _format_trace(self, record: pd.Series, score: int) -> str:
        """Formats a single trace record into a human-readable string for LLM prompts."""
        lines = [f"--- ELK Trace Match (Score: {score}) ---"]
        for col, val in record.items():
            lines.append(f"{col}: {val}")
        return "\n".join(lines)

# Singleton instance for easy access across the application
elk_engine = ELK()
