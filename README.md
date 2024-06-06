![](https://drive.google.com/uc?export=view&id=1UwPIfBrG021siM9SBAku2JNqG4R6avs6)

<div align="center">    
 
# Retrieve, Read and LinK: Fast and Accurate Entity Linking and Relation Extraction on an Academic Budget

[![Conference](http://img.shields.io/badge/ACL-2024-4b44ce.svg)](https://2024.aclweb.org/)
[![Paper](http://img.shields.io/badge/paper-ACL--anthology-B31B1B.svg)](https://aclanthology.org/)
[![arXiv](https://img.shields.io/badge/arXiv-placeholder-b31b1b.svg)](https://arxiv.org/abs/placeholder)

[![Open in Visual Studio Code](https://img.shields.io/badge/preview%20in-vscode.dev-blue)](https://github.dev/SapienzaNLP/relik)
[![PyTorch](https://img.shields.io/badge/PyTorch-orange?logo=pytorch)](https://pytorch.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000)](https://github.com/psf/black)
[![Upload to PyPi](https://github.com/SapienzaNLP/relik/actions/workflows/python-publish-pypi.yml/badge.svg)](https://github.com/SapienzaNLP/relik/actions/workflows/python-publish-pypi.yml)
[![PyPi Version](https://img.shields.io/github/v/release/SapienzaNLP/relik)](https://github.com/SapienzaNLP/relik/releases)

</div>

A blazing fast and lightweight Information Extraction model for Entity Linking and Relation Extraction.

## Installation

Installation from PyPI

```console
pip install relik
```

<details>
  <summary>Other installation options</summary>

#### Install with optional dependencies

Install with all the optional dependencies.

```console
pip install relik[all]
```

Install with optional dependencies for training and evaluation.

```console
pip install relik[train]
```

Install with optional dependencies for [FAISS](https://github.com/facebookresearch/faiss)

```console
pip install relik[faiss] # or relik[faiss-gpu] for GPU support
```

Install with optional dependencies for serving the models with [FastAPI](https://fastapi.tiangolo.com/) and [Ray](https://docs.ray.io/en/latest/serve/quickstart.html).

```console
pip install relik[serve]
```

#### Installation from source

```console
git clone https://github.com/SapienzaNLP/relik.git
cd relik
pip install -e .[all]
```

</details>

## Quick Start

[//]: # (Write a short description of the model and how to use it with the `from_pretrained` method.)

ReLiK is a lightweight and fast model for **Entity Linking** and **Relation Extraction**. It is composed of two main components: a retriever and a reader. The retriever is responsible for retrieving relevant documents from a large collection of documents, while the reader is responsible for extracting entities and relations from the retrieved documents. ReLiK can be used with the `from_pretrained` method to load a pre-trained pipeline.

Here is an example of how to use ReLiK for Entity Linking:

```python
from relik import Relik

relik = Relik.from_pretrained("sapienzanlp/relik-entity-linking-large")
relik("Michael Jordan was one of the best players in the NBA.")
```

and for Relation Extraction:

```python
from relik import Relik

relik = Relik.from_pretrained("sapienzanlp/relik-relation-extraction-large")
relik("Michael Jordan was one of the best players in the NBA.")
```

The full list of available models can be found on [🤗 Hugging Face](https://huggingface.co/collections/sapienzanlp/relik-retrieve-read-and-link-665d9e4a5c3ecba98c1bef19).

Retrievers and Readers can be used separately:

```python
from relik import Relik

# If you want to use the retriever only
retriever = Relik.from_pretrained("sapienzanlp/relik-relation-extraction-large", reader=None)

# If you want to use the reader only
reader = Relik.from_pretrained("sapienzanlp/relik-relation-extraction-large", retriever=None)
```
<!-- 
or

```python
from relik.retriever import GoldenRetriever

# If you want to use the retriever only
retriever = GoldenRetriever(
    question_encoder="path/to/relik/retriever-question-encoder",
    document_index="path/to/relik/retriever-document-index",
)

from relik.reader import R
# If you want to use the reader only
reader = 
``` -->

## Before You Start

In the following sections, we provide a step-by-step guide on how to prepare the data, train the retriever and reader, and evaluate the model.

### Entity Linking

All your data should have the following starting structure:

```jsonl
{
  "doc_id": int,  # Unique identifier for the document
  "doc_text": txt,  # Text of the document
  "doc_annotations": # Char level annotations
    [
      [start, end, label],
      [start, end, label],
      ...
    ]
}
```

We used BLINK (Wu et al., 2019) and AIDA (Hoffart et al, 2011) datasets for training and evaluation.
More specifically, we used the BLINK dataset for pre-training the retriever and the AIDA dataset for fine-tuning the retriever and training the reader.

The BLINK dataset can be downloaded from the [GENRE](https://github.com/facebookresearch/GENRE) repo from [here](https://github.com/facebookresearch/GENRE/blob/main/scripts_genre/download_all_datasets.sh).
We used `blink-train-kilt.jsonl` and `blink-dev-kilt.jsonl` as training and validation datasets.
Assuming we have downloaded the two files in the `data/blink` folder, we converted the BLINK dataset to the ReLiK format using the following script:

```console
# Train
python scripts/data/blink/preprocess_genre_blink.py \
  data/blink/blink-train-kilt.jsonl \
  data/blink/processed/blink-train-kilt-relik.jsonl

# Dev
python scripts/data/blink/preprocess_genre_blink.py \
  data/blink/blink-dev-kilt.jsonl \
  data/blink/processed/blink-dev-kilt-relik.jsonl
```

The AIDA dataset is not publicly available, but we provide the file we used without `text` field. You can find the file in ReLiK format in `data/aida/processed` folder.

The Wikipedia index we used can be downloaded from [here](https://huggingface.co/sapienzanlp/relik-retriever-e5-base-v2-aida-blink-wikipedia-index/blob/main/documents.jsonl).

### Relation Extraction

TODO

## Retriever

We perform a two-step training process for the retriever. First, we "pre-train" the retriever using BLINK (Wu et al., 2019) dataset and then we "fine-tune" it using AIDA (Hoffart et al, 2011).

### Data Preparation

The retriever requires a dataset in a format similar to [DPR](https://github.com/facebookresearch/DPR): a `jsonl` file where each line is a dictionary with the following keys:

```json lines
{
  "question": "....",
  "positive_ctxs": [{
    "title": "...",
    "text": "...."
  }],
  "negative_ctxs": [{
    "title": "...",
    "text": "...."
  }],
  "hard_negative_ctxs": [{
    "title": "...",
    "text": "...."
  }]
}
```

The retriever also needs an index to search for the documents. The documents to index can be either a jsonl file or a tsv file similar to
[DPR](https://github.com/facebookresearch/DPR):

- `jsonl`: each line is a json object with the following keys: `id`, `text`, `metadata`
- `tsv`: each line is a tab-separated string with the `id` and `text` column,
  followed by any other column that will be stored in the `metadata` field

jsonl example:

```json lines
{
  "id": "...",
  "text": "...",
  "metadata": ["{...}"]
},
...
```

tsv example:

```tsv
id \t text \t any other column
...
```

#### Entity Linking

##### BLINK

Once you have the BLINK dataset in the ReLiK format, you can create the windows with the following script:

```console
# train
python scripts/data/create_windows.py \
  data/blink/processed/blink-train-kilt-relik.jsonl \
  data/blink/processed/blink-train-kilt-relik-windowed.jsonl

# dev
python scripts/data/create_windows.py \
  data/blink/processed/blink-dev-kilt-relik.jsonl \
  data/blink/processed/blink-dev-kilt-relik-windowed.jsonl
```

and then convert it to the DPR format:

```console
# train
python scripts/data/blink/convert_to_dpr.py \
  data/blink/processed/blink-train-kilt-relik-windowed.jsonl \
  data/blink/processed/blink-train-kilt-relik-windowed-dpr.jsonl

# dev
python scripts/data/blink/convert_to_dpr.py \
  data/blink/processed/blink-dev-kilt-relik-windowed.jsonl \
  data/blink/processed/blink-dev-kilt-relik-windowed-dpr.jsonl
```

##### AIDA

Since the AIDA dataset is not publicly available, we can provide the annotations for the AIDA dataset in the ReLiK format as an example.
Assuming you have the full AIDA dataset in the `data/aida`, you can convert it to the ReLiK format and then create the windows with the following script:

```console
python scripts/data/create_windows.py \
  data/data/processed/aida-train-relik.jsonl \
  data/data/processed/aida-train-relik-windowed.jsonl
```

and then convert it to the DPR format:

```console
python scripts/data/convert_to_dpr.py \
  data/data/processed/aida-train-relik-windowed.jsonl \
  data/data/processed/aida-train-relik-windowed-dpr.jsonl
```

### Training the model

The `relik retriever train` command can be used to train the retriever. It requires the following arguments:

- `config_path`: The path to the configuration file.
- `overrides`: A list of overrides to the configuration file, in the format `key=value`.

Examples of configuration files can be found in the `relik/retriever/conf` folder.

#### Entity Linking

<!-- You can find an example in `relik/retriever/conf/finetune_iterable_in_batch.yaml`. -->
The configuration files in `relik/retriever/conf` are `pretrain_iterable_in_batch.yaml` and `finetune_iterable_in_batch.yaml`, which we used to pre-train and fine-tune the retriever, respectively.

For instance, to train the retriever on the AIDA dataset, you can run the following command:

```console
relik retriever train relik/retriever/conf/finetune_iterable_in_batch.yaml \
  model.language_model=intfloat/e5-base-v2 \
  train_dataset_path=data/aida/processed/aida-train-relik-windowed-dpr.jsonl \
  val_dataset_path=data/aida/processed/aida-dev-relik-windowed-dpr.jsonl \
  test_dataset_path=data/aida/processed/aida-test-relik-windowed-dpr.jsonl
```

#### Relation Extraction

TODO

### Inference

By passing `train.only_test=True` to the `relik retriever train` command, you can skip the training and only evaluate the model.
It needs also the path to the PyTorch Lightning checkpoint and the dataset to evaluate on.

```console
relik retriever train relik/retriever/conf/finetune_iterable_in_batch.yaml \
  train.only_test=True \
  test_dataset_path=data/aida/processed/aida-test-relik-windowed-dpr.jsonl
  model.checkpoint_path=path/to/checkpoint
```

The retriever encoder can be saved from the checkpoint with the following command:

```python
from relik.retriever.lightning_modules.pl_modules import GoldenRetrieverPLModule

checkpoint_path = "path/to/checkpoint"
retriever_folder = "path/to/retriever"

# If you want to push the model to the Hugging Face Hub set push_to_hub=True
push_to_hub = False
# If you want to push the model to the Hugging Face Hub set the repo_id
repo_id = "sapienzanlp/relik-retriever-e5-base-v2-aida-blink-encoder"

pl_module = GoldenRetrieverPLModule.load_from_checkpoint(checkpoint_path)
pl_module.model.save_pretrained(retriever_folder, push_to_hub=push_to_hub, repo_id=repo_id)
```

with `push_to_hub=True` the model will be pushed to the 🤗 Hugging Face Hub with `repo_id` the repository id where the model will be pushed.

The retriever needs a index to search for the documents. The index can be created using `create_index.py` script in `scripts/data/retriever`

```console

python scripts/data/retriever/create_index.py -h 

usage: Create retriever index. [-h] --question-encoder-name-or-path QUESTION_ENCODER_NAME_OR_PATH --document-path DOCUMENT_PATH [--passage-encoder-name-or-path PASSAGE_ENCODER_NAME_OR_PATH] [--indexer_class INDEXER_CLASS]
                               [--document-file-type DOCUMENT_FILE_TYPE] --output-folder OUTPUT_FOLDER [--batch-size BATCH_SIZE] [--passage-max-length PASSAGE_MAX_LENGTH] [--device DEVICE] [--index-device INDEX_DEVICE] [--precision PRECISION]
                               [--num-workers NUM_WORKERS] [--push-to-hub] [--repo-id REPO_ID]

options:
  -h, --help            show this help message and exit
  --question-encoder-name-or-path QUESTION_ENCODER_NAME_OR_PATH
  --document-path DOCUMENT_PATH
  --passage-encoder-name-or-path PASSAGE_ENCODER_NAME_OR_PATH
  --indexer_class INDEXER_CLASS
  --document-file-type DOCUMENT_FILE_TYPE
  --output-folder OUTPUT_FOLDER
  --batch-size BATCH_SIZE
  --passage-max-length PASSAGE_MAX_LENGTH
  --device DEVICE
  --index-device INDEX_DEVICE
  --precision PRECISION
  --num-workers NUM_WORKERS
  --push-to-hub
  --repo-id REPO_ID
```

With the encoder and the index, the retriever can be loaded from a repo id or a local path:

```python
from relik.retriever import GoldenRetriever

encoder_name_or_path = "sapienzanlp/relik-retriever-e5-base-v2-aida-blink-encoder"
index_name_or_path = "sapienzanlp/relik-retriever-e5-base-v2-aida-blink-wikipedia-index"

retriever = GoldenRetriever(
  question_encoder=encoder_name_or_path,
  document_index=index_name_or_path,
  device="cuda", # or "cpu"
  precision="16", # or "32", "bf16"
  index_device="cuda", # or "cpu"
  index_precision="16", # or "32", "bf16"
)
```

and then it can be used to retrieve documents:

```python
retriever.retrieve("Michael Jordan was one of the best players in the NBA.", top_k=100)
```

## Reader

The reader is responsible for extracting entities and relations from documents from a set of candidates (e.g., possible entities or relations).
The reader can be trained for span extraction or triplet extraction.
The `RelikReaderForSpanExtraction` is used for span extraction, i.e. Entity Linking , while the `RelikReaderForTripletExtraction` is used for triplet extraction, i.e. Relation Extraction.

### Data Preparation

The reader requires the windowized dataset we created in section [Before You Start](#before-you-start) augmented with the candidate from the retriever.
The candidate can be added to the dataset using the `add_candidates.py` script in `scripts/data/retriever`.

```console
python scripts/data/retriever/add_candidates.py -h

usage: Add the candidates to the windowized dataset [-h] --question-encoder-name-or-path QUESTION_ENCODER_NAME_OR_PATH --document-name-or-path DOCUMENT_NAME_OR_PATH [--passage-encoder-name-or-path PASSAGE_ENCODER_NAME_OR_PATH] --input-path INPUT_PATH
                                                    --output-path OUTPUT_PATH [--top-k TOP_K] [--batch-size BATCH_SIZE] [--device DEVICE] [--index-device INDEX_DEVICE] [--precision PRECISION] [--use-doc-topics] [--num-workers NUM_WORKERS] [--log-recall]

options:
  -h, --help            show this help message and exit
  --question-encoder-name-or-path QUESTION_ENCODER_NAME_OR_PATH
  --document-name-or-path DOCUMENT_NAME_OR_PATH
  --passage-encoder-name-or-path PASSAGE_ENCODER_NAME_OR_PATH
  --input-path INPUT_PATH
  --output-path OUTPUT_PATH
  --top-k TOP_K
  --batch-size BATCH_SIZE
  --device DEVICE
  --index-device INDEX_DEVICE
  --precision PRECISION
  --use-doc-topics
  --num-workers NUM_WORKERS
  --log-recall
```

### Training the model

Similar to the retriever, the `relik reader train` command can be used to train the retriever. It requires the following arguments:

- `config_path`: The path to the configuration file.
- `overrides`: A list of overrides to the configuration file, in the format `key=value`.

Examples of configuration files can be found in the `relik/reader/conf` folder.

#### Entity Linking

The configuration files in `relik/reader/conf` are `large.yaml` and `base.yaml`, which we used to train the large and base reader, respectively.
For instance, to train the large reader on the AIDA dataset run:

```console
relik reader train relik/reader/conf/large.yaml \
  train_dataset_path=data/aida/processed/aida-train-relik-windowed-candidates.jsonl \
  val_dataset_path=data/aida/processed/aida-dev-relik-windowed-candidates.jsonl \
  test_dataset_path=data/aida/processed/aida-dev-relik-windowed-candidates.jsonl
```

#### Relation Extraction

TODO

### Inference

The reader can be saved from the checkpoint with the following command:

```python
from relik.reader.lightning_modules.relik_reader_pl_module import RelikReaderPLModule

checkpoint_path = "path/to/checkpoint"
reader_folder = "path/to/reader"

# If you want to push the model to the Hugging Face Hub set push_to_hub=True
push_to_hub = False
# If you want to push the model to the Hugging Face Hub set the repo_id
repo_id = "sapienzanlp/relik-reader-deberta-v3-large-aida"

pl_model = RelikReaderPLModule.load_from_checkpoint(
    trainer.checkpoint_callback.best_model_path
)
pl_model.relik_reader_core_model.save_pretrained(experiment_path, push_to_hub=push_to_hub, repo_id=repo_id)
```

with `push_to_hub=True` the model will be pushed to the 🤗 Hugging Face Hub with `repo_id` the repository id where the model will be pushed.

The reader can be loaded from a repo id or a local path:

```python
from relik.reader import RelikReaderForSpanExtraction, RelikReaderForTripletExtraction

# the reader for span extraction
reader_span = RelikReaderForSpanExtraction(
  "sapienzanlp/relik-reader-deberta-v3-large-aida"
)
# the reader for triplet extraction
reader_tripltes = RelikReaderForTripletExtraction(
  "sapienzanlp/relik-reader-deberta-v3-large-nyt"
)
```

and used to extract entities and relations:

```python
# an example of candidates for the reader
candidates = ["Michael Jordan", "NBA", "Chicago Bulls", "Basketball", "United States"]
reader_span.read("Michael Jordan was one of the best players in the NBA.", candidates=candidates)
```

## Performance

### Entity Linking

We evaluate the performance of ReLiK on Entity Linking using [GERBIL](http://gerbil-qa.aksw.org/gerbil/). The following table shows the results (InKB Micro F1) of ReLiK Large and Base:

| Model | AIDA-B | MSNBC | Der | K50 | R128 | R500 | OKE15 | OKE16 | AVG | AVG-OOD | Speed (ms) |
|-------|--------|-------|-----|-----|------|------|-------|-------|-----|---------|------------|
| Base | 85.25 | 72.27 | 55.59 | 68.02 | 48.13 | 41.61 | 62.53 | 52.25 | 60.71 | 57.2 | n |
| Large | 86.37 | 75.04 | 56.25 | 72.8 | 51.67 | 42.95 | 65.12 | 57.21 | 63.43 | 60.15 | n |

To evaluate ReLiK we use the following steps:

1. Download the GERBIL server from [here](LINK).

2. Start the GERBIL server:

```console
cd gerbil && ./start.sh
```

2. Start the following services:

```console
cd gerbil-SpotWrapNifWS4Test && mvn clean -Dmaven.tomcat.port=1235 tomcat:run
```

3. Start the ReLiK server for GERBIL providing the model name as an argument (e.g. `sapienzanlp/relik-entity-linking-large`):

```console
python relik/reader/utils/gerbil_server.py --relik-model-name sapienzanlp/relik-entity-linking-large
```

4. Open the url [http://localhost:1234/gerbil](http://localhost:1234/gerbil) and:
   - Select A2KB as experiment type
   - Select "Ma - strong annotation match"
   - In Name filed write the name you want to give to the experiment
   - In URI field write: [http://localhost:1235/gerbil-spotWrapNifWS4Test/myalgorithm](http://localhost:1235/gerbil-spotWrapNifWS4Test/myalgorithm)
   - Select the datasets (We use AIDA-B, MSNBC, Der, K50, R128, R500, OKE15, OKE16)
   - Finally, run experiment

### Relation Extraction

- TODO

## Cite this work

If you use any part of this work, please consider citing the paper as follows:

```bibtex
@inproceedings{orlando-etal-2024-relik,
    title     = "Retrieve, Read and LinK: Fast and Accurate Entity Linking and Relation Extraction on an Academic Budget",
    author    = "Orlando, Riccardo and Huguet Cabot, Pere-Llu{\'\i}s and Barba, Edoardo and Navigli, Roberto",
    booktitle = "Findings of the Association for Computational Linguistics: ACL 2024",
    month     = aug,
    year      = "2024",
    address   = "Bangkok, Thailand",
    publisher = "Association for Computational Linguistics",
}
```

## License

TODO
<!-- The data is licensed under [Creative Commons Attribution-ShareAlike 4.0](https://creativecommons.org/licenses/by-sa/4.0/). -->
