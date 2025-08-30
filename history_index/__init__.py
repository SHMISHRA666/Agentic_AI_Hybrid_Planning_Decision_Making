from typing import TYPE_CHECKING

# Avoid importing submodules at package import time to prevent
# runpy RuntimeWarning when executing `python -m history_index.indexer`.
if TYPE_CHECKING:  # for type checkers only, no runtime import
    from .indexer import HistoryIndexer
    from .retriever import HistoryRetriever

__all__ = ["HistoryIndexer", "HistoryRetriever"]


