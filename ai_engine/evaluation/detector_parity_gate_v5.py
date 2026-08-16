"""Tight held-out detector and downstream FDI stability gate."""
import json,math,statistics
from collections import Counter
from pathlib import Path
import numpy as np,onnxruntime as ort,torch
from PIL import Image
from torchvision.transforms.functional import to_tensor
from ai_engine.onnx.export_dentai_v5_onnx import detector_models
from ai_engine.inference import dentai_unified_v5_onnx as ox
from ai_engine.evaluation.master_evaluate_v5 import records_for_tooth,pathology_records,restoration_records

OUT=Path('artifacts/evaluation/dentai_v5_detector_parity_gate.json')
def pct(v,p):return sorted(v)[max(0,math.ceil(p*len(v))-1)]if v else 0
def matches(ab,al,bb,bl):
 c=sorted(((ox.iou(a,b)[0],i,j)for i,a in enumerate(ab)for j,b in enumerate(bb)if int(al[i])==int(bl[j])),reverse=True);out=[];ua=set();ub=set()
 for q,i,j in c:
  if q<.5:break
  if i not in ua and j not in ub:ua.add(i);ub.add(j);out.append((i,j,q))
 return out
def main():
 specs=detector_models();pre=ort.InferenceSession('models/onnx/dentai_v5/detector_preprocess.onnx',providers=['CPUExecutionProvider']);datasets={'tooth':records_for_tooth()[:50],'pathology':pathology_records('test')[:50],'restoration_detector':restoration_records('test')};results={};fdi={'images':0,'tooth_count_agreement':0,'raw_agree':0,'raw_total':0,'resolved_agree':0,'resolved_total':0,'pt_duplicates':0,'onnx_duplicates':0,'pt_unique':0,'onnx_unique':0,'wrong_to_correct':0,'correct_to_wrong':0};fs=ort.InferenceSession('models/onnx/dentai_v5/fdi_v3.onnx',providers=['CPUExecutionProvider'])
 for key,(model,fn,_)in specs.items():
  s=ort.InferenceSession('models/onnx/dentai_v5/'+fn,providers=['CPUExecutionProvider']);ious=[];centers=[];scores=[];totp=toto=clsok=0
  for r in datasets[key]:
   im=Image.open(r['image_path']).convert('RGB');x=to_tensor(im)
   with torch.inference_mode():a=model([x])[0]
   mn,mx=(800,1333)if key=='restoration_detector'else(640,1600);b,bs,bl=ox.detect(s,pre,im,mn,mx);ai=[i for i,v in enumerate(a['scores'])if float(v)>=.5];bi=[i for i,v in enumerate(bs)if float(v)>=.5];ab=[a['boxes'][i].tolist()for i in ai];bb=[b[i].tolist()for i in bi];al=[int(a['labels'][i])for i in ai];blo=[int(bl[i])for i in bi];m=matches(ab,al,bb,blo);totp+=len(ai);toto+=len(bi);clsok+=len(m)
   for i,j,q in m:
    ious.append(q);centers.append(math.hypot((ab[i][0]+ab[i][2]-bb[j][0]-bb[j][2])/2,(ab[i][1]+ab[i][3]-bb[j][1]-bb[j][3])/2));scores.append(abs(float(a['scores'][ai[i]])-float(bs[bi[j]])))
   if key=='tooth':
    def rows(boxes,ss):
     z=[]
     for n,(box,score)in enumerate(zip(boxes,ss)):
      p=ox.fdi_probs(fs,im,box);z.append({'id':n,'bbox':box,'probs':p,'raw':ox.FDI[int(p.argmax())],'raw_conf':float(p.max()),'score':score})
     return z
    ar=rows(ab,[float(a['scores'][i])for i in ai]);br=rows(bb,[float(bs[i])for i in bi]);ares=ox.resolve(ar);bres=ox.resolve(br);am={z['id']:z for z in ares};bm={z['id']:z for z in bres};fdi['images']+=1;fdi['tooth_count_agreement']+=len(ab)==len(bb);fdi['pt_duplicates']+=len(ar)-len(set(z['resolved']for z in ares));fdi['onnx_duplicates']+=len(br)-len(set(z['resolved']for z in bres));fdi['pt_unique']+=len(set(z['resolved']for z in ares));fdi['onnx_unique']+=len(set(z['resolved']for z in bres))
    for i,j,_ in m:
     fdi['raw_total']+=1;fdi['resolved_total']+=1;fdi['raw_agree']+=ar[i]['raw']==br[j]['raw'];fdi['resolved_agree']+=am[i]['resolved']==bm[j]['resolved'];fdi['wrong_to_correct']+=ar[i]['raw']!=br[j]['raw']and am[i]['resolved']==bm[j]['resolved'];fdi['correct_to_wrong']+=ar[i]['raw']==br[j]['raw']and am[i]['resolved']!=bm[j]['resolved']
  results[key]={'images':len(datasets[key]),'pytorch_detections':totp,'onnx_detections':toto,'matched_iou_050':len(ious),'matched_iou_075':sum(x>=.75 for x in ious),'matched_iou_090':sum(x>=.9 for x in ious),'mean_iou':statistics.mean(ious),'median_iou':statistics.median(ious),'p5_iou':pct(ious,.05),'class_agreement':clsok/len(ious),'mean_center_delta':statistics.mean(centers),'p95_center_delta':pct(centers,.95),'mean_score_difference':statistics.mean(scores)};print(key,results[key])
 fdi['tooth_count_agreement_rate']=fdi['tooth_count_agreement']/fdi['images'];fdi['raw_agreement']=fdi['raw_agree']/fdi['raw_total'];fdi['resolved_agreement']=fdi['resolved_agree']/fdi['resolved_total'];results['fdi_stability']=fdi;OUT.write_text(json.dumps(results,indent=2,allow_nan=False));print('FDI',fdi)
if __name__=='__main__':main()
