import collections
import itertools
from typing import Dict, List, Optional, Set, Tuple

from relik.inference.data.splitters.blank_sentence_splitter import BlankSentenceSplitter
from relik.inference.data.splitters.base_sentence_splitter import BaseSentenceSplitter
from relik.inference.data.tokenizers.base_tokenizer import BaseTokenizer
from relik.reader.data.relik_reader_sample import RelikReaderSample


class WindowManager:
    def __init__(
        self, tokenizer: BaseTokenizer, splitter: BaseSentenceSplitter | None = None
    ) -> None:
        self.tokenizer = tokenizer
        self.splitter = splitter or BlankSentenceSplitter()

    def create_windows(
        self,
        documents: str | List[str],
        window_size: int | None = None,
        stride: int | None = None,
        max_length: Optional[int] = None,
        doc_topic: str = None,
        is_split_into_words: bool = False,
        mentions: List[List[List[int]]] = None,
    ) -> Tuple[List[RelikReaderSample], List[RelikReaderSample]]:
        """
        Create windows from a list of documents.

        Args:
            documents (:obj:`str` or :obj:`List[str]`):
                The document(s) to split in windows.
            window_size (:obj:`int`):
                The size of the window.
            stride (:obj:`int`):
                The stride between two windows.
            max_length (:obj:`int`, `optional`):
                The maximum length of a window.
            doc_topic (:obj:`str`, `optional`):
                The topic of the document(s).
            is_split_into_words (:obj:`bool`, `optional`, defaults to :obj:`False`):
                Whether the input is already pre-tokenized (e.g., split into words). If :obj:`False`, the
                input will first be tokenized using the tokenizer, then the tokens will be split into words.
            mentions (:obj:`List[List[List[int]]]`, `optional`):
                The mentions of the document(s).

        Returns:
            :obj:`List[RelikReaderSample]`: The windows created from the documents.
        """
        # normalize input
        if isinstance(documents, str) or is_split_into_words:
            documents = [documents]

        # batch tokenize
        documents_tokens = self.tokenizer(
            documents, is_split_into_words=is_split_into_words
        )

        # set splitter params
        if hasattr(self.splitter, "window_size"):
            self.splitter.window_size = window_size or self.splitter.window_size
        if hasattr(self.splitter, "window_stride"):
            self.splitter.window_stride = stride or self.splitter.window_stride

        windowed_documents, windowed_blank_documents = [], []

        if mentions is not None:
            assert len(documents) == len(
                mentions
            ), f"documents and mentions should have the same length, got {len(documents)} and {len(mentions)}"
            doc_iter = zip(documents, documents_tokens, mentions)
        else:
            doc_iter = zip(documents, documents_tokens, itertools.repeat([]))

        for doc_id, (document, document_tokens, document_mentions) in enumerate(
            doc_iter
        ):
            if doc_topic is None:
                doc_topic = document_tokens[0] if len(document_tokens) > 0 else ""

            splitted_document = self.splitter(document_tokens, max_length=max_length)

            document_windows = []
            for window_id, window in enumerate(splitted_document):
                window_text_start = window[0].idx
                window_text_end = window[-1].idx + len(window[-1].text)
                if isinstance(document, str):
                    text = document[window_text_start:window_text_end]
                else:
                    # window_text_start = window[0].idx
                    # window_text_end = window[-1].i
                    text = " ".join([w.text for w in window])
                sample = RelikReaderSample(
                    doc_id=doc_id,
                    window_id=window_id,
                    text=text,
                    tokens=[w.text for w in window],
                    words=[w.text for w in window],
                    doc_topic=doc_topic,
                    offset=window_text_start,
                    spans=[
                        [m[0], m[1]] for m in document_mentions 
                        if window_text_end > m[0] >= window_text_start and window_text_end >= m[1] >= window_text_start
                    ],
                    token2char_start={str(i): w.idx for i, w in enumerate(window)},
                    token2char_end={
                        str(i): w.idx + len(w.text) for i, w in enumerate(window)
                    },
                    char2token_start={
                        str(w.idx): w.i for i, w in enumerate(window)
                    },
                    char2token_end={
                        str(w.idx + len(w.text)): w.i for i, w in enumerate(window)
                    },
                )
                if mentions is not None and len(sample.spans) == 0:
                    windowed_blank_documents.append(sample)
                else:
                    document_windows.append(sample)

            windowed_documents.extend(document_windows)
        return windowed_documents, windowed_blank_documents

    def merge_windows(
        self, windows: List[RelikReaderSample]
    ) -> List[RelikReaderSample]:
        windows_by_doc_id = collections.defaultdict(list)
        for window in windows:
            windows_by_doc_id[window.doc_id].append(window)

        merged_window_by_doc = {
            doc_id: self._merge_doc_windows(doc_windows)
            for doc_id, doc_windows in windows_by_doc_id.items()
        }

        return list(merged_window_by_doc.values())

    def _merge_doc_windows(self, windows: List[RelikReaderSample]) -> RelikReaderSample:
        if len(windows) == 1:
            return windows[0]

        if len(windows) > 0 and getattr(windows[0], "offset", None) is not None:
            windows = sorted(windows, key=(lambda x: x.offset))

        window_accumulator = windows[0]

        for next_window in windows[1:]:
            window_accumulator = self._merge_window_pair(
                window_accumulator, next_window
            )

        return window_accumulator

    @staticmethod
    def _merge_tokens(
        window1: RelikReaderSample, window2: RelikReaderSample
    ) -> Tuple[list, dict, dict]:
        w1_tokens = window1.tokens[1:-1]
        w2_tokens = window2.tokens[1:-1]

        # find intersection if any
        tokens_intersection = 0
        for k in reversed(range(1, len(w1_tokens))):
            if w1_tokens[-k:] == w2_tokens[:k]:
                tokens_intersection = k
                break

        final_tokens = (
            [window1.tokens[0]]  # CLS
            + w1_tokens
            + w2_tokens[tokens_intersection:]
            + [window1.tokens[-1]]  # SEP
        )

        w2_starting_offset = len(w1_tokens) - tokens_intersection

        def merge_char_mapping(t2c1: dict, t2c2: dict) -> dict:
            final_t2c = dict()
            final_t2c.update(t2c1)
            for t, c in t2c2.items():
                t = int(t)
                if t < tokens_intersection:
                    continue
                final_t2c[str(t + w2_starting_offset)] = c
            return final_t2c

        return (
            final_tokens,
            merge_char_mapping(window1.token2char_start, window2.token2char_start),
            merge_char_mapping(window1.token2char_end, window2.token2char_end),
        )

    @staticmethod
    def _merge_words(
        window1: RelikReaderSample, window2: RelikReaderSample
    ) -> Tuple[list, dict, dict]:
        w1_words = window1.words
        w2_words = window2.words

        # find intersection if any
        words_intersection = 0
        for k in reversed(range(1, len(w1_words))):
            if w1_words[-k:] == w2_words[:k]:
                words_intersection = k
                break

        final_words = w1_words + w2_words[words_intersection:]

        w2_starting_offset = len(w1_words) - words_intersection

        def merge_word_mapping(t2c1: dict, t2c2: dict) -> dict:
            final_t2c = dict()
            if t2c1 is None:
                t2c1 = dict()
            if t2c2 is None:
                t2c2 = dict()
            final_t2c.update(t2c1)
            for t, c in t2c2.items():
                t = int(t)
                if t < words_intersection:
                    continue
                final_t2c[str(t + w2_starting_offset)] = c
            return final_t2c

        return (
            final_words,
            merge_word_mapping(window1.token2word_start, window2.token2word_start),
            merge_word_mapping(window1.token2word_end, window2.token2word_end),
        )

    @staticmethod
    def _merge_span_annotation(
        span_annotation1: List[list], span_annotation2: List[list]
    ) -> List[list]:
        uniq_store = set()
        final_span_annotation_store = []
        for span_annotation in itertools.chain(span_annotation1, span_annotation2):
            span_annotation_id = tuple(span_annotation)
            if span_annotation_id not in uniq_store:
                uniq_store.add(span_annotation_id)
                final_span_annotation_store.append(span_annotation)
        return sorted(final_span_annotation_store, key=lambda x: x[0])

    @staticmethod
    def _merge_predictions(
        window1: RelikReaderSample, window2: RelikReaderSample
    ) -> Tuple[Set[Tuple[int, int, str]], dict]:
        # a RelikReaderSample should have a filed called `predicted_spans`
        # that stores the span-level predictions, or a filed called
        # `predicted_triples` that stores the triple-level predictions

        # span predictions
        merged_span_predictions: Set = set()
        merged_span_probabilities = dict()
        # triple predictions
        merged_triplet_predictions: Set = set()
        merged_triplet_probs: Dict = dict()

        if (
            getattr(window1, "predicted_spans", None) is not None
            and getattr(window2, "predicted_spans", None) is not None
        ):
            merged_span_predictions = set(window1.predicted_spans).union(
                set(window2.predicted_spans)
            )
            merged_span_predictions = sorted(merged_span_predictions)
            # probabilities
            for span_prediction, predicted_probs in itertools.chain(
                window1.probs_window_labels_chars.items()
                if window1.probs_window_labels_chars is not None
                else [],
                window2.probs_window_labels_chars.items()
                if window2.probs_window_labels_chars is not None
                else [],
            ):
                if span_prediction not in merged_span_probabilities:
                    merged_span_probabilities[span_prediction] = predicted_probs

            if (
                getattr(window1, "predicted_triples", None) is not None
                and getattr(window2, "predicted_triples", None) is not None
            ):
                # try to merge the triples predictions
                # add offset to the second window
                window1_triplets = [
                    (
                        merged_span_predictions.index(window1.predicted_spans[t[0]]),
                        t[1],
                        merged_span_predictions.index(window1.predicted_spans[t[2]]),
                        t[3]
                    )
                    for t in window1.predicted_triples
                ]
                window2_triplets = [
                    (
                        merged_span_predictions.index(window2.predicted_spans[t[0]]),
                        t[1],
                        merged_span_predictions.index(window2.predicted_spans[t[2]]),
                        t[3]
                    )
                    for t in window2.predicted_triples
                ]
                merged_triplet_predictions = set(window1_triplets).union(
                    set(window2_triplets)
                )
                merged_triplet_predictions = sorted(merged_triplet_predictions)
                # for now no triplet probs, we don't need them for the moment

        return (
            merged_span_predictions,
            merged_span_probabilities,
            merged_triplet_predictions,
            merged_triplet_probs,
        )

    @staticmethod
    def _merge_candidates(window1: RelikReaderSample, window2: RelikReaderSample):
        candidates = []
        windows_candidates = []

        # TODO: retro-compatibility
        if getattr(window1, "candidates", None) is not None:
            candidates = window1.candidates
        if getattr(window2, "candidates", None) is not None:
            candidates += window2.candidates

        # TODO: retro-compatibility
        if getattr(window1, "windows_candidates", None) is not None:
            windows_candidates = window1.windows_candidates
        if getattr(window2, "windows_candidates", None) is not None:
            windows_candidates += window2.windows_candidates

        # TODO: add programmatically
        span_candidates = []
        if getattr(window1, "span_candidates", None) is not None:
            span_candidates = window1.span_candidates
        if getattr(window2, "span_candidates", None) is not None:
            span_candidates += window2.span_candidates

        triplet_candidates = []
        if getattr(window1, "triplet_candidates", None) is not None:
            triplet_candidates = window1.triplet_candidates
        if getattr(window2, "triplet_candidates", None) is not None:
            triplet_candidates += window2.triplet_candidates

        # make them unique
        candidates = list(set(candidates))
        windows_candidates = list(set(windows_candidates))

        span_candidates = list(set(span_candidates))
        triplet_candidates = list(set(triplet_candidates))

        return candidates, windows_candidates, span_candidates, triplet_candidates

    def _merge_window_pair(
        self,
        window1: RelikReaderSample,
        window2: RelikReaderSample,
    ) -> RelikReaderSample:
        merging_output = dict()

        if getattr(window1, "doc_id", None) is not None:
            assert window1.doc_id == window2.doc_id

        if getattr(window1, "offset", None) is not None:
            assert (
                window1.offset < window2.offset
            ), f"window 2 offset ({window2.offset}) is smaller that window 1 offset({window1.offset})"

        merging_output["doc_id"] = window1.doc_id
        merging_output["offset"] = window2.offset

        m_tokens, m_token2char_start, m_token2char_end = self._merge_tokens(
            window1, window2
        )

        m_words, m_token2word_start, m_token2word_end = self._merge_words(
            window1, window2
        )

        (
            m_candidates,
            m_windows_candidates,
            m_span_candidates,
            m_triplet_candidates,
        ) = self._merge_candidates(window1, window2)

        window_labels = None
        if getattr(window1, "window_labels", None) is not None:
            window_labels = self._merge_span_annotation(
                window1.window_labels, window2.window_labels
            )

        (
            predicted_spans,
            predicted_spans_probs,
            predicted_triples,
            predicted_triples_probs,
        ) = self._merge_predictions(window1, window2)

        merging_output.update(
            dict(
                tokens=m_tokens,
                words=m_words,
                token2char_start=m_token2char_start,
                token2char_end=m_token2char_end,
                token2word_start=m_token2word_start,
                token2word_end=m_token2word_end,
                window_labels=window_labels,
                candidates=m_candidates,
                span_candidates=m_span_candidates,
                triplet_candidates=m_triplet_candidates,
                windows_candidates=m_windows_candidates,
                predicted_spans=predicted_spans,
                predicted_spans_probs=predicted_spans_probs,
                predicted_triples=predicted_triples,
                predicted_triples_probs=predicted_triples_probs,
            )
        )

        return RelikReaderSample(**merging_output)
