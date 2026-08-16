"""Non-destructive dynamic INT8 experiment for parity-passed classifiers."""
import json
from pathlib import Path
import numpy as np,onnxruntime as ort
from onnxruntime.quantization import QuantType,quantize_dynamic
from PIL import Image
from ai_engine.inference import dentai_unified_v5_onnx as ox
from ai_engine.evaluation.master_evaluate_v5 import restoration_records
ROOT=Path('models/onnx/dentai_v5');OUT=Path('artifacts/evaluation/dentai_v5_onnx_int8.json')
def run(name,items,inputs):
 items=items[:50];opts=ort.SessionOptions();opts.intra_op_num_threads=4;opts.inter_op_num_threads=1
 a=ort.InferenceSession(str(ROOT/(name+'.onnx')),sess_options=opts,providers=['CPUExecutionProvider']);b=ort.InferenceSession(str(ROOT/(name+'_int8.onnx')),sess_options=opts,providers=['CPUExecutionProvider']);agree=0;mx=total=count=0
 for i in range(0,len(items),64):
  feed=tuple(np.concatenate([z[j]for z in items[i:i+64]],axis=0)for j in range(len(inputs)))
  x=a.run(None,{k:v for k,v in zip(inputs,feed)})[0];y=b.run(None,{k:v for k,v in zip(inputs,feed)})[0];d=np.abs(x-y);mx=max(mx,float(d.max()));total+=float(d.sum());count+=d.size;agree+=int((x.argmax(1)==y.argmax(1)).sum())
 return {'samples':len(items),'prediction_agreement':agree/len(items),'max_abs_logit_difference':mx,'mean_abs_logit_difference':total/count,'accepted':agree==len(items)}
def main():
 names=['fdi_v3','status_gate_v1','status_v2','deep_caries_v2','restoration_classifier_v1']
 for n in names:
  if not (ROOT/(n+'_int8.onnx')).exists():quantize_dynamic(str(ROOT/(n+'.onnx')),str(ROOT/(n+'_int8.onnx')),weight_type=QuantType.QInt8)
 superd=json.load(open('data/canonical/dentai_v3_super/test.json'))['records'];fdi=[];deep=[]
 for r in superd:
  im=Image.open(r['image_path']).convert('RGB');W,H=im.size
  for x in r.get('instances',[]):
   b=x.get('bbox_xyxy')
   if len(fdi)<50 and x.get('canonical_class')=='TOOTH'and b:
    x1,y1,x2,y2=map(float,b);sp=np.array([[(x1+x2)/2/W,(y1+y2)/2/H,(x2-x1)/W,(y2-y1)/H]],np.float32);fdi.append((ox.crop(im,b,.35,12,224),sp))
   if len(deep)<50 and x.get('source_disease')in('Caries','Deep Caries')and b:deep.append((ox.crop(im,b,.55,24,256),))
 status=[];gate=[]
 for r in json.load(open('data/canonical/dual_labeled_status/test.json'))['records']:
  im=Image.open(r['image_path']).convert('RGB')
  for x in r['teeth']:
   if len(status)<50:gate.append((ox.crop(im,x['bbox_xyxy'],.35,16,224),));status.append((ox.crop(im,x['bbox_xyxy'],.45,18,256),))
 rest=[]
 for r in restoration_records('test'):
  im=Image.open(r['image_path']).convert('RGB')
  for x in r['objects']:
   if len(rest)<50:rest.append((ox.crop(im,x['bbox'],.45,15,224),))
 result={'fdi_v3':run('fdi_v3',fdi,['image','spatial']),'status_gate_v1':run('status_gate_v1',gate,['image']),'status_v2':run('status_v2',status,['image']),'deep_caries_v2':run('deep_caries_v2',deep,['image']),'restoration_classifier_v1':run('restoration_classifier_v1',rest,['image'])};OUT.write_text(json.dumps(result,indent=2,allow_nan=False));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
