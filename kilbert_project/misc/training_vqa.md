# VQA
* Training 1 : vilbert-job-0.1.dev491-ga8ed80a.d20200922182615
* Validation/Evaluation from Training 1 : vilbert-job-0.1.dev492-g62dfbf2.d20200924143315


## Training
In comparaison of the best results procedure (with 2 training, 1 validation, 1 evaluation), I had run just one training on the VQA dataset.


Update the template file `vilbert-job-train-model3_vqa_MZ.tpl`:
```console
python3 -u train_tasks.py --model_version 3 --bert_model=bert-base-uncased --from_pretrained_kilbert None --from_pretrained=/nas-data/vilbert/data2/kilbert_base_model/pytorch_model_9.bin --config_file config/bert_base_6layer_6conect.json --output_dir=/nas-data/vilbert/outputs/JOB_NAME_PLACEHOLDER-JOB_ID_PLACEHOLDER --num_workers 16 --tasks 0
```
* tasks 0: run on the VQA dataset


## Validation
Validation is based on the first training results (using "pytorch_model_19.bin").


Update the template file `vilbert-job-eval-model3_okvqa_MZ.tpl`:
```
python3 -u eval_tasks.py --model_version 3 --bert_model=bert-base-uncased --from_pretrained=/nas-data/vilbert/data2/save_final/VQA_bert_base_6layer_6conect-beta_vilbert_vqa/pytorch_model_11.bin  --from_pretrained_kilbert=/nas-data/vilbert/outputs/vilbert-job-0.1.dev492-g62dfbf2.d20200924004919/VQA_bert_base_6layer_6conect/pytorch_model_19.bin --config_file config/bert_base_6layer_6conect.json --output_dir=/nas-data/vilbert/outputs/JOB_NAME_PLACEHOLDER-JOB_ID_PLACEHOLDER --num_workers 16 --tasks 0 --split val
```
* from_pretrained_kilbert: change the value with the result of the previous training path
* tasks 0: run on the VQA dataset


### Evaluation

Update `vqaEval_okvqa.py` file with the following values:
```console
data_dir = '/nas-data/vilbert/data2/VQA' #VQA version
annFile = "%s/v2_%s_%s_annotations.json" % (data_dir, dataType, dataSubType)
quesFile = "%s/v2_%s_%s_%s_questions.json" % (data_dir, taskType, dataType, dataSubType)
```

Update the template file `vilbert-job-evaluation_vqa.tpl`:
```console
python kilbert/PythonEvaluationTools/vqaEval_okvqa.py --json_dir /nas-data/vilbert/outputs/vilbert-job-0.1.dev493-g91a003c.d20200924185447/ --output_dir /nas-data/vilbert/outputs/vilbert-job-0.1.dev493-g91a003c.d20200924185447/
```
* json_dir: change the value with the result of the validation path
* output_dir: change the value with the result of the validation path (same path as json_dir)
