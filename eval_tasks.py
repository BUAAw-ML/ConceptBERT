### LIBRARIES ###
# Global libraries
import os
import sys
import argparse
import logging
from easydict import EasyDict as edict

from io import open
import json
import yaml
import random

import numpy as np

import torch
import torch.nn as nn
import torch.distributed as dist

# Custom libraries
from task_utils import (
    LoadDatasetEval,
    LoadLosses,
    EvaluatingModel,
)
import utils as utils
from load_conceptBert import load_conceptBert

### LOGGER CONFIGURATION ###

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s -   %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

### MAIN FUNCTION ###


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--model_version",
        default=3,
        type=int,
        help="Which version of the model you want to use",
    )

    parser.add_argument(
        "--bert_model",
        default="bert-base-uncased",
        type=str,
        help="Bert pre-trained model selected in the list: bert-base-uncased, "
        "bert-large-uncased, bert-base-cased, bert-base-multilingual, bert-base-chinese.",
    )
    parser.add_argument(
        "--from_pretrained",
        default="bert-base-uncased",
        type=str,
        help="Bert pre-trained model selected in the list: bert-base-uncased, "
        "bert-large-uncased, bert-base-cased, bert-base-multilingual, bert-base-chinese.",
    )
    parser.add_argument(
        "--from_pretrained_conceptBert",
        default="bert-base-uncased",
        type=str,
        help="Bert pre-trained model selected in the list: bert-base-uncased, "
        "bert-large-uncased, bert-base-cased, bert-base-multilingual, bert-base-chinese.",
    )
    parser.add_argument(
        "--conceptBert_path", type=str, help="Path to the pretrained ConceptBert model",
    )
    parser.add_argument(
        "--output_dir",
        default="results",
        type=str,
        help="The output directory where the model checkpoints will be written.",
    )
    parser.add_argument(
        "--config_file",
        default="config/bert_config.json",
        type=str,
        help="The config file which specified the model details.",
    )
    parser.add_argument(
        "--no_cuda", action="store_true", help="Whether not to use CUDA when available"
    )
    parser.add_argument(
        "--do_lower_case",
        default=True,
        type=bool,
        help="Whether to lower case the input text. True for uncased models, False for cased models.",
    )
    parser.add_argument(
        "--local_rank",
        type=int,
        default=-1,
        help="local_rank for distributed training on gpus",
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="random seed for initialization"
    )
    parser.add_argument(
        "--fp16",
        action="store_true",
        help="Whether to use 16-bit float precision instead of 32-bit",
    )
    parser.add_argument(
        "--loss_scale",
        type=float,
        default=0,
        help="Loss scaling to improve fp16 numeric stability. Only used when fp16 set to True.\n"
        "0 (default value): dynamic loss scaling.\n"
        "Positive power of 2: static loss scaling value.\n",
    )
    parser.add_argument(
        "--num_workers",
        type=int,
        default=10,
        help="Number of workers in the dataloader.",
    )
    parser.add_argument(
        "--save_name", default="", type=str, help="save name for training.",
    )
    parser.add_argument(
        "--batch_size", default=1000, type=int, help="what is the batch size?"
    )
    parser.add_argument(
        "--tasks", default="", type=str, help="1-2-3... training task separate by -"
    )
    parser.add_argument(
        "--in_memory",
        default=False,
        type=bool,
        help="whether use chunck for parallel training.",
    )
    parser.add_argument("--split", default="", type=str, help="which split to use.")

    args = parser.parse_args()
    with open("vlbert_tasks.yml", "r") as f:
        task_cfg = edict(yaml.safe_load(f))

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    # Load main module
    from conceptBert.bert_pretrained_model import BertConfig
    from conceptBert.conceptbert_models import ConceptBert

    task_names = []
    for i, task_id in enumerate(args.tasks.split("-")):
        task = "TASK" + task_id
        name = task_cfg[task]["name"]
        task_names.append(name)

    # timeStamp = '-'.join(task_names) + '_' + args.config_file.split('/')[1].split('.')[0]
    timeStamp = args.from_pretrained.split("/")[1] + "-" + args.save_name

    output_dir = args.output_dir
    savePath = os.path.join(output_dir, timeStamp)

    config = BertConfig.from_json_file(args.config_file)
    bert_weight_name = json.load(
        open("config/" + args.bert_model + "_weight_name.json", "r")
    )

    if args.local_rank == -1 or args.no_cuda:
        device = torch.device(
            "cuda" if torch.cuda.is_available() and not args.no_cuda else "cpu"
        )
        n_gpu = torch.cuda.device_count()
    else:
        torch.cuda.set_device(args.local_rank)
        device = torch.device("cuda", args.local_rank)
        n_gpu = 1
        torch.distributed.init_process_group(backend="nccl")
    print("DEVICE: ", device)
    print("N_GPU: ", n_gpu)
    logger.info(
        "device: {} n_gpu: {}, distributed training: {}, 16-bits training: {}".format(
            device, n_gpu, bool(args.local_rank != -1), args.fp16
        )
    )

    default_gpu = False
    if dist.is_available() and args.local_rank != -1:
        rank = dist.get_rank()
        if rank == 0:
            default_gpu = True
    else:
        default_gpu = True

    if default_gpu and not os.path.exists(savePath):
        os.makedirs(savePath)

    (
        task_batch_size,
        task_num_iters,
        task_ids,
        task_datasets_val,
        task_dataloader_val,
    ) = LoadDatasetEval(args, task_cfg, args.tasks.split("-"))

    tbLogger = utils.tbLogger(
        timeStamp,
        savePath,
        task_names,
        task_ids,
        task_num_iters,
        1,
        save_logger=False,
        txt_name="eval.txt",
    )

    num_labels = max([dataset.num_labels for dataset in task_datasets_val.values()])

    """
    model = ConceptBert.from_pretrained(
        args.from_pretrained,
        config,
        split="val",
        num_labels=num_labels,
        default_gpu=default_gpu,
    )
    """
    """
    model = ConceptBert(
        args.from_pretrained,
        args.model_version,
        config,
        num_labels,
        args.tasks,
        split="val",
        default_gpu=default_gpu,
    )
    """
    model = ConceptBert(
        args.from_pretrained,
        args.model_version,
        config,
        num_labels,
        args.tasks,
        split="val",
        default_gpu=default_gpu,
    )
    # model.load_state_dict(torch.load(args.conceptBert_path))
    model = load_conceptBert(model, args.from_pretrained_conceptBert)

    task_losses = LoadLosses(args, task_cfg, args.tasks.split("-"))
    model.to(device)
    if args.local_rank != -1:
        try:
            from apex.parallel import DistributedDataParallel as DDP
        except ImportError:
            raise ImportError(
                "Please install apex from https://www.github.com/nvidia/apex to use distributed and fp16 training."
            )
        model = DDP(model, delay_allreduce=True)

    elif n_gpu > 1:
        model = nn.DataParallel(model)

    no_decay = ["bias", "LayerNorm.bias", "LayerNorm.weight"]

    print("  Num Iters: ", task_num_iters)
    print("  Batch size: ", task_batch_size)

    if args.tasks == "0":
        dataset = "vqa"
    elif args.tasks == "42":
        dataset = "ok_vqa"

    model.eval()
    for task_id in task_ids:
        results = []
        others = []
        for i, batch in enumerate(task_dataloader_val[task_id]):
            loss, score, batch_size, results, others = EvaluatingModel(
                args,
                task_cfg,
                device,
                task_id,
                batch,
                model,
                task_dataloader_val,
                task_losses,
                results,
                others,
                dataset,
            )

            tbLogger.step_val(0, float(loss), float(score), task_id, batch_size, "val")

            sys.stdout.write("%d/%d\r" % (i, len(task_dataloader_val[task_id])))
            sys.stdout.flush()
        # save the result or evaluate the result.
        ave_score = tbLogger.showLossVal()

        if args.split:
            json_path = os.path.join(savePath, args.split)
        else:
            json_path = os.path.join(savePath, task_cfg[task_id]["val_split"])

        path_brut='./nas-data/'
        json.dump(results, open(output_dir + "/val_result.json", "w"))
        json.dump(others, open(output_dir + "/val_others.json", "w"))
        print("************DONE writing")

if __name__ == "__main__":
    main()
