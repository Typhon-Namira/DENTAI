"""ONNX Runtime CPU thread/load/RAM benchmark for accepted DENTAI V5."""
import json,statistics,time
from pathlib import Path
from ai_engine.inference.dentai_unified_v5_onnx import Engine
OUTJ=Path('artifacts/evaluation/dentai_v5_onnx_cpu_benchmark.json');OUTT=Path('artifacts/evaluation/dentai_v5_onnx_cpu_benchmark.txt')
def p95(x):return sorted(x)[max(0,int(.95*len(x)+.999)-1)]
def rss():
 for line in Path('/proc/self/status').read_text().splitlines():
  if line.startswith('VmRSS:'):return int(line.split()[1])*1024
 return 0
def main():
 rows=json.load(open('data/canonical/dual_labeled_status/test.json'))['records'][:3];allr={}
 for threads in(1,2,4):
  before=rss();t=time.perf_counter();e=Engine(threads);load=time.perf_counter()-t;loaded=rss();times=[]
  for r in rows:s=time.perf_counter();e.analyze(r['image_path']);times.append(time.perf_counter()-s)
  peak=rss();allr[str(threads)]={'threads':threads,'images':len(times),'model_load_seconds':load,'mean_seconds_per_image':statistics.mean(times),'median_seconds_per_image':statistics.median(times),'p95_seconds_per_image':p95(times),'rss_before_bytes':before,'rss_after_load_bytes':loaded,'rss_after_inference_bytes':peak,'model_rss_delta_bytes':max(0,loaded-before)};print(threads,allr[str(threads)]);del e
 result={'provider':'CPUExecutionProvider','models':'FP32','configurations':allr,'note':'Three identical held-out images per thread setting; PyTorch 20-image reference mean was 11.1190 s/image.'};OUTJ.write_text(json.dumps(result,indent=2,allow_nan=False));OUTT.write_text('\n'.join(f"{k} threads: mean={v['mean_seconds_per_image']:.4f}s median={v['median_seconds_per_image']:.4f}s p95={v['p95_seconds_per_image']:.4f}s load={v['model_load_seconds']:.4f}s RSSdelta={v['model_rss_delta_bytes']}"for k,v in allr.items())+'\n')
if __name__=='__main__':main()
