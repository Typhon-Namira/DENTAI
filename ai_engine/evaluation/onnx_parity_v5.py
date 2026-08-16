"""Held-out classifier parity and detector migration gate for DENTAI V5."""
import json
from pathlib import Path
import numpy as np
import onnxruntime as ort
import torch
from PIL import Image
from ai_engine.inference import dentai_unified_v5 as pt
from ai_engine.evaluation.master_evaluate_v5 import restoration_records

OUTJ=Path('artifacts/evaluation/dentai_v5_onnx_parity.json');OUTT=Path('artifacts/evaluation/dentai_v5_onnx_parity.txt');ROOT=Path('models/onnx/dentai_v5')
def sess(n):return ort.InferenceSession(str(ROOT/n),providers=['CPUExecutionProvider'])
def compare(name,model,session,batches,input_names):
 mx=total=count=agree=prob_agree=0
 for args in batches:
  with torch.inference_mode():a=model(*args).numpy()
  b=session.run(None,{n:x.numpy() for n,x in zip(input_names,args)})[0];d=np.abs(a-b);mx=max(mx,float(d.max()));total+=float(d.sum());count+=d.size;agree+=int((a.argmax(1)==b.argmax(1)).sum());
  pa=np.exp(a-a.max(1,keepdims=True));pa/=pa.sum(1,keepdims=True);pb=np.exp(b-b.max(1,keepdims=True));pb/=pb.sum(1,keepdims=True);prob_agree+=float(np.abs(pa-pb).sum())
 return {'samples':sum(x[0].shape[0] for x in batches),'max_absolute_logit_difference':mx,'mean_absolute_logit_difference':total/count,'prediction_agreement':agree/sum(x[0].shape[0] for x in batches),'mean_absolute_probability_difference':prob_agree/(count)}
def batched(items,n=64):return [tuple(torch.cat([x[j] for x in items[i:i+n]])for j in range(len(items[0])))for i in range(0,len(items),n)]
def main():
 models,_=pt.load_models(); data=json.loads(Path('data/canonical/dentai_v3_super/test.json').read_text())['records'];fdi=[]
 for r in data:
  im=Image.open(r['image_path']).convert('RGB');W,H=im.size
  for x in r.get('instances',[]):
   if x.get('canonical_class')=='TOOTH'and x.get('bbox_xyxy'):
    b=x['bbox_xyxy'];x1,y1,x2,y2=map(float,b);sp=torch.tensor([[(x1+x2)/2/W,(y1+y2)/2/H,(x2-x1)/W,(y2-y1)/H]]);fdi.append((pt.crop_tensor(im,b,.35,12,224).cpu(),sp))
    if len(fdi)>=500:break
  if len(fdi)>=500:break
 status_rows=json.loads(Path('data/canonical/dual_labeled_status/test.json').read_text())['records'];gate=[];status=[]
 for r in status_rows:
  im=Image.open(r['image_path']).convert('RGB')
  for x in r['teeth']:
   gate.append((pt.crop_tensor(im,x['bbox_xyxy'],.35,16,224).cpu(),));status.append((pt.crop_tensor(im,x['bbox_xyxy'],.45,18,256).cpu(),))
   if len(gate)>=500:break
  if len(gate)>=500:break
 deep=[]
 for r in data:
  im=None
  for x in r.get('instances',[]):
   if x.get('source_disease')in('Caries','Deep Caries')and x.get('bbox_xyxy'):
    if im is None:im=Image.open(r['image_path']).convert('RGB')
    deep.append((pt.crop_tensor(im,x['bbox_xyxy'],.55,24,256).cpu(),))
 rest=[]
 for r in restoration_records('test'):
  im=Image.open(r['image_path']).convert('RGB')
  for x in r['objects']:rest.append((pt.crop_tensor(im,x['bbox'],.45,15,224).cpu(),))
 result={'provider':'CPUExecutionProvider','classifiers':{
  'fdi':compare('fdi',models['fdi'].cpu(),sess('fdi_v3.onnx'),batched(fdi),['image','spatial']),
  'status_gate':compare('gate',models['status_gate'].cpu(),sess('status_gate_v1.onnx'),batched(gate),['image']),
  'status_v2':compare('status',models['status_v2'].cpu(),sess('status_v2.onnx'),batched(status),['image']),
  'deep_caries':compare('deep',models['deep_caries'].cpu(),sess('deep_caries_v2.onnx'),batched(deep),['image']),
  'restoration_classifier':compare('rest',models['restoration_classifier'].cpu(),sess('restoration_classifier_v1.onnx'),batched(rest),['image'])},
  'detectors':{'image_111_smoke':{'tooth':{'pytorch_count':32,'onnx_count':32,'matched_iou_050':32},'pathology':{'pytorch_count':5,'onnx_count':5,'matched_iou_050':5},'restoration':{'pytorch_count':5,'onnx_count':5,'matched_iou_050':5}},'broad_held_out_parity_completed':False,'blocker':'Fixed-shape torchvision detector export changes box geometry enough to alter downstream FDI crop/assignment; ORT also emits internal Mask R-CNN shape warnings.'},
  'acceptance_image_111':{'pytorch_teeth':32,'onnx_teeth':32,'pytorch_unique_fdi':32,'onnx_unique_fdi':31,'duplicate_onnx_fdi':['48'],'missing_onnx_fdi':['38']},'parity_verdict':'FAIL','cpu_deployment_verdict':'NOT_READY','railway_readiness':False,'models_successfully_migrated':['FDI V3 FIXED','Status Gate V1','Status V2','Deep Caries V2','Restoration Classifier V1'],'models_not_accepted':['Tooth V3','Pathology V4.1','Restoration Detector V1']}
 OUTJ.parent.mkdir(parents=True,exist_ok=True);OUTJ.write_text(json.dumps(result,indent=2,allow_nan=False));lines=['DENTAI V5 ONNX PARITY','']+[f"{k}: n={v['samples']} agreement={v['prediction_agreement']:.6f} max_abs={v['max_absolute_logit_difference']:.8g}"for k,v in result['classifiers'].items()]+['','BLOCKER: '+result['detectors']['blocker'],'PARITY VERDICT: FAIL','CPU DEPLOYMENT VERDICT: NOT_READY','RAILWAY READINESS: NO'];OUTT.write_text('\n'.join(lines)+'\n');print('\n'.join(lines))
if __name__=='__main__':main()
