# -*- coding: utf-8 -*-
"""Step4 v1.1 Experiment - Minimal"""
import sys, io, json, re, argparse
from pathlib import Path
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

MERGE_KW_THRESHOLD = 1

def kw(text):
    return set(re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}', text.lower()))

def overlap(a, b):
    ka = kw(a.get("gap",""))
    for st in a.get("source_trace",[]):
        ka.update(kw(st.get("quoted_content","")))
    kb = kw(b.get("gap",""))
    for st in b.get("source_trace",[]):
        kb.update(kw(st.get("quoted_content","")))
    return len(ka & kb) >= MERGE_KW_THRESHOLD

def merge(a, b):
    po = {"P0":0,"P1":1,"P2":2,"P3":3}
    p = po.get(a.get("priority","P3"),9) <= po.get(b.get("priority","P3"),9)
    pri, sec = (a,b) if p else (b,a)
    m = dict(pri)
    m["priority"] = pri.get("priority")
    src = set(pri.get("source",[])) | set(sec.get("source",[]))
    m["source"] = list(src)
    traces = pri.get("source_trace",[]) + sec.get("source_trace",[])
    seen = set()
    dedup = []
    for t in traces:
        key = (t.get("step",""), t.get("field",""), t.get("id_or_index",""))
        if key not in seen:
            seen.add(key)
            dedup.append(t)
    m["source_trace"] = dedup
    if len(sec.get("gap","")) > len(pri.get("gap","")):
        m["gap"] = sec["gap"]
    m["why_it_matters"] = (pri.get("why_it_matters","") + " | " + sec.get("why_it_matters",""))[:500]
    return m

def dedup(gaps):
    if not gaps: return []
    used = [False]*len(gaps)
    out = []
    for i in range(len(gaps)):
        if used[i]: continue
        cur = dict(gaps[i])
        for j in range(i+1, len(gaps)):
            if used[j]: continue
            if overlap(cur, gaps[j]):
                cur = merge(cur, gaps[j])
                used[j] = True
        used[i] = True
        p = cur.get("priority","P3")
        idx = 1 + sum(1 for g in out if g.get("priority")==p)
        cur["gap_id"] = f"gap_{p.lower()}_{idx}"
        out.append(cur)
    return out

def p0(step2):
    gaps = []
    blockers = (step2.get("information_resolution") or {}).get("decision_blockers", [])
    for i,b in enumerate(blockers):
        c = b if isinstance(b,str) else json.dumps(b, ensure_ascii=False)
        gaps.append({"gap_id":f"gap_p0_{i+1}","gap":c,"priority":"P0",
                     "source":["step2"],"source_trace":[{"step":"step2","field":"information_resolution.decision_blockers","id_or_index":str(i),"quoted_content":c[:200]}],
                     "why_it_matters":"Step2 一票否决项，不解决则其他问题无意义。","question_to_ask":"","good_answer":"","bad_answer":"","go_criteria":"","no_go_criteria":""})
    return gaps

def _match_s3(kw_set, step3, used):
    hits = []
    for i,t in enumerate(step3.get("tensions",[])):
        if i in used: continue
        if len(kw(json.dumps(t,ensure_ascii=False)) & kw_set) >= MERGE_KW_THRESHOLD:
            hits.append(("tension",i,t))
            used.add(i)
    for i,p in enumerate(step3.get("overpackaging_signals",[])):
        if i in used: continue
        if len(kw(json.dumps(p,ensure_ascii=False)) & kw_set) >= MERGE_KW_THRESHOLD:
            hits.append(("packaging",i,p))
            used.add(i)
    return hits

def p1(step2, step3):
    gaps = []
    checks = (step2.get("step1_external_check") or {}).get("checks", [])
    ca = [c for c in checks if isinstance(c,dict) and c.get("verdict") in ("caution","contradict")]
    used_s3 = set()
    for ci,c in enumerate(ca):
        cc_kw = kw(json.dumps(c, ensure_ascii=False))
        matched = _match_s3(cc_kw, step3, used_s3)
        if not matched: continue
        c_content = c.get("reasoning") or c.get("external_logic","")
        s3_str = " | ".join(json.dumps(x, ensure_ascii=False)[:120] for _,_,x in matched)
        gap = {"gap_id":f"gap_p1_{ci+1}","priority":"P1","source":["step2","step3"],
                "gap":f"Step2: {c_content[:120]} | Step3: {s3_str[:120]}",
                "source_trace":[{"step":"step2","field":"step1_external_check.checks","id_or_index":str(ci),"quoted_content":c_content[:200]}]
                    + [{"step":"step3","field":f"{t}s","id_or_index":str(i),"quoted_content":json.dumps(o,ensure_ascii=False)[:200]} for t,i,o in matched],
                "why_it_matters":"Step2 外部约束与 Step3 包装识别同向，独立分析汇聚的风险点。",
                "question_to_ask":"","good_answer":"","bad_answer":"","go_criteria":"","no_go_criteria":""}
        gaps.append(gap)
    return gaps

def p2(step3):
    gaps = []
    for i,cc in enumerate(step3.get("consistency_checks",[])):
        if not isinstance(cc,dict): continue
        if cc.get("judgement") not in ("contradict","uncertain"): continue
        gaps.append({"gap_id":f"gap_p2_cc_{i+1}","priority":"P2","source":["step3"],
                     "source_trace":[{"step":"step3","field":"consistency_checks","id_or_index":str(i),
                                     "quoted_content":f"topic={cc.get('topic','')}, gap={cc.get('gap','')}, judgement={cc.get('judgement','')}"}],
                     "gap":cc.get("gap",cc.get("topic","")),
                     "why_it_matters":"Step3 识别到叙事内部矛盾，需现场核实。","question_to_ask":"","good_answer":"","bad_answer":"","go_criteria":"","no_go_criteria":""})
    used = set()
    for g in gaps:
        for st in g.get("source_trace",[]):
            used.add(("consistency_checks", int(st.get("id_or_index","-1"))))
    for i,p in enumerate(step3.get("overpackaging_signals",[])):
        if ("overpackaging_signals",i) in used: continue
        gaps.append({"gap_id":f"gap_p2_op_{i+1}","priority":"P2","source":["step3"],
                     "source_trace":[{"step":"step3","field":"overpackaging_signals","id_or_index":str(i),
                                     "quoted_content":p.get("signal",p.get("type",""))}],
                     "gap":p.get("signal",p.get("type","")),
                     "why_it_matters":"Step3 识别到包装信号，需现场核实。","question_to_ask":"","good_answer":"","bad_answer":"","go_criteria":"","no_go_criteria":""})
    return gaps

def p3(step1):
    gaps = []
    rf = step1.get("red_flags") or {}
    flags = (rf.get("flags") if isinstance(rf,dict) else rf) or []
    for i,f in enumerate(flags):
        gaps.append({"gap_id":f"gap_p3_rf_{i+1}","priority":"P3","source":["step1"],
                     "source_trace":[{"step":"step1","field":"red_flags","id_or_index":str(i),
                                     "quoted_content":(f if isinstance(f,str) else json.dumps(f,ensure_ascii=False))}],
                     "gap":f if isinstance(f,str) else json.dumps(f,ensure_ascii=False),
                     "why_it_matters":"Step1 识别的风险点，常规尽调需核实。","question_to_ask":"","good_answer":"","bad_answer":"","go_criteria":"","no_go_criteria":""})
    ma = step1.get("must_ask_questions") or {}
    qs = (ma.get("questions") if isinstance(ma,dict) else ma) or []
    for i,q in enumerate(qs):
        gaps.append({"gap_id":f"gap_p3_ma_{i+1}","priority":"P3","source":["step1"],
                     "source_trace":[{"step":"step1","field":"must_ask_questions","id_or_index":str(i),
                                     "quoted_content":(q if isinstance(q,str) else json.dumps(q,ensure_ascii=False))}],
                     "gap":q if isinstance(q,str) else json.dumps(q,ensure_ascii=False),
                     "why_it_matters":"Step1 提出的必问问题。","question_to_ask":(q if isinstance(q,str) else ""),
                     "good_answer":"","bad_answer":"","go_criteria":"","no_go_criteria":""})
    return gaps

def fill_q(gaps):
    for g in gaps:
        if g.get("question_to_ask"): continue
        txt = g.get("gap","")
        if "代运营" in txt:
            g["question_to_ask"] = "代运营模式中，车辆是自持还是租赁？如果是自持，这一轮融资够买多少台？"
            g["good_answer"] = "已锁定XX台车辆租赁合同，租金锁定X年，IRR超过XX%"
            g["bad_answer"] = "还在和物流公司谈，车辆成本由客户承担"
        elif "技术" in txt or "壁垒" in txt:
            g["question_to_ask"] = "请具体说明技术壁垒在哪里？有没有量化数据或第三方验证？"
            g["good_answer"] = "有具体场景下的量化数据（如感知延迟低于XXms，运营里程超过XX万公里）"
            g["bad_answer"] = "只有demo视频或概念描述，无实际运营数据"
        elif "客户" in txt or "合同" in txt:
            g["question_to_ask"] = "能给我看一个已签约的客户合同吗？合同金额、交付条款、付款周期是怎样的？"
            g["good_answer"] = "能提供已签约客户合同，含金额、交付条款、付款周期"
            g["bad_answer"] = "只有意向书/MOU，或回答'客户不方便提供合同'"
        else:
            g["question_to_ask"] = f"关于「{txt[:30]}」，请提供具体证据（合同/数据/第三方验证）。"
            g["good_answer"] = "有具体数字/合同/数据支持"
            g["bad_answer"] = "只有概念描述，无实质证据"
    return gaps

def meeting_path(gaps):
    opening, deepening, trap = [], [], []
    for g in gaps:
        p = g.get("priority","P3")
        item = {"purpose":g.get("why_it_matters","")[:100],"question":g.get("question_to_ask",""),"source":p}
        if p=="P0":
            trap.append({"purpose":item["purpose"],"question":item["question"],"if_avoided":"说明BP对该问题没有合理答案，建议NO-GO","source":p})
        elif p in ("P1","P2"):
            deepening.append({"purpose":item["purpose"],"leading_question":item["question"],"follow_up":"连续追问具体数字/合同/数据","trap":f"如果拿掉「{g.get('gap','')[:20]}」这个说法，BP叙事是否还成立？","source":p})
        else:
            opening.append(item)
    return {"opening_questions":opening[:2],"deepening_questions":deepening[:4],"trap_questions":trap[:2]}

def run(step1, step2, step3, pname):
    print(f"[{pname}] Building gaps...")
    g0 = p0(step2)
    print(f"  P0: {len(g0)}")
    g1 = p1(step2, step3)
    print(f"  P1: {len(g1)}")
    g2 = p2(step3)
    print(f"  P2: {len(g2)}")
    g3 = p3(step1)
    print(f"  P3: {len(g3)}")
    all_g = g0+g1+g2+g3
    print(f"  Total before dedup: {len(all_g)}")
    deduped = dedup(all_g)
    print(f"  Total after dedup: {len(deduped)}")
    filled = fill_q(deduped)
    path = meeting_path(filled)
    out = {"schema_version":"step4_v1_1","project_name":pname,
            "decision_gaps":filled,
            "meeting_question_path":path,
            "decision_summary":{"top_3_must_know":[g.get("gap","")[:80] for g in filled[:3]],
                                 "meeting_goal":f"通过{len(filled)}个核心问题的答案，建立或推翻估值叙事的合理性"},
            "meta":{"p0_count":len(g0),"p1_count":len(g1),"p2_count":len(g2),"p3_count":len(g3),
                    "dedup_removed":len(all_g)-len(deduped)}}
    return out

def save(out, pname):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    d = Path(f"step4_v11_experiment_{ts}") / pname
    d.mkdir(parents=True, exist_ok=True)
    (d/"step4_exp.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    # markdown report
    lines = [f"# Step4 v1.1 Report: {pname}", f"**Schema**: {out.get('schema_version')}", ""]
    meta = out.get("meta",{})
    lines += [f"P0: {meta.get('p0_count')}", f"P1: {meta.get('p1_count')}", f"P2: {meta.get('p2_count')}", f"P3: {meta.get('p3_count')}", f"Dedup removed: {meta.get('dedup_removed')}", ""]
    for g in out.get("decision_gaps",[]):
        lines += [f"### {g.get('gap_id')} [{g.get('priority')}]", f"Gap: {g.get('gap','')}", f"Source: {', '.join(g.get('source',[]))}"]
        for st in g.get("source_trace",[]):
            lines.append(f"  trace → step={st.get('step')}, field={st.get('field')}, quote={st.get('quoted_content','')[:100]}")
        lines += [f"Q: {g.get('question_to_ask','')}", f"Good: {g.get('good_answer','')}", f"Bad: {g.get('bad_answer','')}", ""]
    path = out.get("meeting_question_path",{})
    lines += ["## Meeting Path", f"Opening: {json.dumps(path.get('opening_questions',[]), ensure_ascii=False)}",
              f"Deepening: {json.dumps(path.get('deepening_questions',[]), ensure_ascii=False)}",
              f"Trap: {json.dumps(path.get('trap_questions',[]), ensure_ascii=False)}"]
    (d/"step4_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"  Saved to: {d}")
    return d

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--projects", nargs="+", default=["A1"])
    ap.add_argument("--workspace", default=r"D:\HuaweiMoveData\Users\86136\Documents\GitHub\investment-assistant\workspace\step1_v1_2_1_experiment")
    args = ap.parse_args()
    ws = Path(args.workspace)
    for pname in args.projects:
        # find latest step1 dir
        s1_dirs = sorted([d for d in (ws).iterdir() if d.is_dir() and d.name.isdigit()], reverse=True)
        step1_path = None
        for d in s1_dirs:
            p = d / pname / "step1_v1_2_1.json"
            if p.exists(): step1_path = p; break
        # find step2
        step2_path = None
        for exp in sorted(ws.iterdir(), reverse=True):
            if exp.is_dir() and "step2_external_check_experiment" in exp.name:
                p = exp / "step2_external_check_v222" / pname / "step2_external_check_v2_2_2.json"
                if p.exists(): step2_path = p; break
        # find step3
        step3_path = None
        for exp in sorted(ws.iterdir(), reverse=True):
            if exp.is_dir() and "step3_v3_experiment" in exp.name:
                p = exp / pname / "step3_exp.json"
                if p.exists(): step3_path = p; break
        print(f"\n{'='*60}")
        print(f"Project: {pname}")
        print(f"  Step1: {step1_path}")
        print(f"  Step2: {step2_path}")
        print(f"  Step3: {step3_path}")
        if not all([step1_path, step2_path, step3_path]):
            print("  SKIP: missing input")
            continue
        step1 = json.loads(step1_path.read_text(encoding="utf-8"))
        step2 = json.loads(step2_path.read_text(encoding="utf-8"))
        step3 = json.loads(step3_path.read_text(encoding="utf-8"))
        out = run(step1, step2, step3, pname)
        save(out, pname)
