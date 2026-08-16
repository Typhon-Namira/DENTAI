"""Twenty-image full Unified V5 PyTorch versus ONNX parity gate."""
import json,time
from pathlib import Path
from PIL import Image
from ai_engine.inference import dentai_unified_v5 as pt
from ai_engine.inference.dentai_unified_v5_onnx import Engine,iou
from ai_engine.evaluation.master_evaluate_v5 import predict_unified
OUT=Path('artifacts/evaluation/dentai_v5_unified_parity_gate.json')
def match(a,b):
 c=sorted(((iou(x['tooth_detection']['bbox_xyxy'],y['tooth_detection']['bbox_xyxy'])[0],i,j)for i,x in enumerate(a)for j,y in enumerate(b)),reverse=True);o=[];u=set();v=set()
 for q,i,j in c:
  if q<.5:break
  if i not in u and j not in v:u.add(i);v.add(j);o.append((i,j,q))
 return o
def main():
 rows=json.load(open('data/canonical/dual_labeled_status/test.json'))['records'][:20];models,_=pt.load_models();oe=Engine(2);items=[];tot={'matched':0,'fdi':0,'gate':0,'status':0,'findings':0,'review':0};pttime=otime=0
 for n,r in enumerate(rows,1):
  im=Image.open(r['image_path']).convert('RGB');a,t=predict_unified(models,im);pttime+=t;s=time.perf_counter();b=oe.analyze(r['image_path'])['teeth'];otime+=time.perf_counter()-s;m=match(a,b);dis=[]
  for i,j,q in m:
   x,y=a[i],b[j];tot['matched']+=1
   checks={'fdi':str(x['fdi'])==str(y['fdi']),'gate':x['status_gate']['prediction']==y['status_gate']['prediction'],'status':x['status_v2']['prediction']==y['status_v2']['prediction'],'findings':set(x['final_findings'])==set(y['final_findings']),'review':x['review_required']==y['review_required']}
   for k,v in checks.items():tot[k]+=v
   if not all(checks.values()):dis.append({'pytorch_fdi':x['fdi'],'onnx_fdi':y['fdi'],'iou':q,'checks':checks,'pytorch_findings':x['final_findings'],'onnx_findings':y['final_findings'],'pytorch_review':x['review_required'],'onnx_review':y['review_required']})
  material=len(a)!=len(b)or len(m)!=len(a)or any(not d['checks']['fdi']or not d['checks']['findings']for d in dis);kind='material'if material else'minor'if dis else'perfect';items.append({'image':r['image_path'],'pytorch_teeth':len(a),'onnx_teeth':len(b),'matched':len(m),'classification':kind,'disagreements':dis});print(n,kind,len(a),len(b),len(dis))
 result={'images':len(items),'perfect_end_to_end':sum(x['classification']=='perfect'for x in items),'minor_differences':sum(x['classification']=='minor'for x in items),'material_differences':sum(x['classification']=='material'for x in items),'matched_teeth':tot['matched'],'fdi_agreement':tot['fdi']/tot['matched'],'status_gate_agreement':tot['gate']/tot['matched'],'status_v2_agreement':tot['status']/tot['matched'],'final_finding_agreement':tot['findings']/tot['matched'],'review_flag_agreement':tot['review']/tot['matched'],'pytorch_mean_seconds':pttime/len(items),'onnx_mean_seconds':otime/len(items),'per_image':items};OUT.write_text(json.dumps(result,indent=2,allow_nan=False));print(json.dumps({k:v for k,v in result.items()if k!='per_image'},indent=2))
if __name__=='__main__':main()
