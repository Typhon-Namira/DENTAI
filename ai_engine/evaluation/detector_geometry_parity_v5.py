"""Diagnose torchvision versus fixed-shape ONNX detector geometry."""
import json,statistics
from pathlib import Path
import numpy as np,onnxruntime as ort,torch
from PIL import Image
from torchvision.transforms.functional import to_tensor
from ai_engine.onnx.export_dentai_v5_onnx import detector_models
from ai_engine.inference.dentai_unified_v5 import intersection_metrics
from ai_engine.inference.dentai_unified_v5_onnx import letterbox
from ai_engine.evaluation.master_evaluate_v5 import records_for_tooth,restoration_records

OUT=Path('artifacts/evaluation/dentai_v5_detector_geometry.json')
def match(a,b,la,lb):
 vals=[];used=set()
 for i,x in enumerate(a):
  choices=[(intersection_metrics(x,b[j])[0],j)for j in range(len(b))if j not in used and int(la[i])==int(lb[j])]
  if not choices:continue
  q,j=max(choices)
  if q>=.5:
   used.add(j);ac=((x[0]+x[2])/2,(x[1]+x[3])/2);y=b[j];bc=((y[0]+y[2])/2,(y[1]+y[3])/2)
   vals.append({'iou':q,'center_delta':((ac[0]-bc[0])**2+(ac[1]-bc[1])**2)**.5,'width_delta':abs((x[2]-x[0])-(y[2]-y[0])),'height_delta':abs((x[3]-x[1])-(y[3]-y[1])),'a':i,'b':j})
 return vals
def main():
 specs=detector_models();tooth=records_for_tooth()[:20];rest=restoration_records('test')[:20];results={}
 for key,(model,fn,shape)in specs.items():
  rows=rest if key=='restoration_detector'else tooth;s=ort.InferenceSession('models/onnx/dentai_v5/'+fn,providers=['CPUExecutionProvider']);items=[]
  for r in rows:
   path=r['image_path'];im=Image.open(path).convert('RGB');x=to_tensor(im);trans,_=model.transform([x]);arr,z,px,py=letterbox(im,shape);normalized=(arr[0]-np.array(model.transform.image_mean,np.float32)[:,None,None])/np.array(model.transform.image_std,np.float32)[:,None,None]
   same=tuple(trans.tensors[0].shape)==tuple(normalized.shape);mad=float(np.abs(trans.tensors[0].numpy()-normalized).mean())if same else None;mxd=float(np.abs(trans.tensors[0].numpy()-normalized).max())if same else None
   with torch.inference_mode():orig=model([x])[0]
   b,sc,l=s.run(None,{'image':arr.astype(np.float32)});b=b.astype(float);b[:,[0,2]]=(b[:,[0,2]]-px)/z;b[:,[1,3]]=(b[:,[1,3]]-py)/z
   ia=[i for i,v in enumerate(orig['scores'])if float(v)>=.5];ib=[i for i,v in enumerate(sc)if float(v)>=.5];m=match([orig['boxes'][i].tolist()for i in ia],[b[i].tolist()for i in ib],[orig['labels'][i]for i in ia],[l[i]for i in ib]);sd=[abs(float(orig['scores'][ia[v['a']]])-float(sc[ib[v['b']]]))for v in m]
   items.append({'image':path,'original_size':[im.height,im.width],'pytorch_transformed_size':list(trans.image_sizes[0]),'pytorch_padded_size':list(trans.tensors.shape),'onnx_input_size':[1,3,*shape],'resize_scale':z,'padding':[py,px],'same_tensor_shape':same,'pixel_mean_absolute_difference':mad,'pixel_max_absolute_difference':mxd,'pytorch_detections':len(ia),'onnx_detections':len(ib),'matched':len(m),'mean_iou':statistics.mean(v['iou']for v in m)if m else 0,'mean_center_delta':statistics.mean(v['center_delta']for v in m)if m else None,'mean_width_delta':statistics.mean(v['width_delta']for v in m)if m else None,'mean_height_delta':statistics.mean(v['height_delta']for v in m)if m else None,'mean_score_delta':statistics.mean(sd)if sd else None})
  results[key]={'images':len(items),'per_image':items,'same_shape_images':sum(x['same_tensor_shape']for x in items),'mean_box_iou':statistics.mean(x['mean_iou']for x in items),'mean_center_delta':statistics.mean(x['mean_center_delta']for x in items if x['mean_center_delta']is not None),'diagnosis':'B/C: fixed ONNX input geometry differs from per-image GeneralizedRCNNTransform; residual traced graph box drift remains even when geometry matches. Mapping is measured separately and is not the primary source.'}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(results,indent=2,allow_nan=False));print(json.dumps({k:{x:y for x,y in v.items()if x!='per_image'}for k,v in results.items()},indent=2))
if __name__=='__main__':main()
