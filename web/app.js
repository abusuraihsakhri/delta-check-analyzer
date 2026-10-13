"use strict";

/* Demo reference values; laboratories must substitute locally validated CVa/CVi. */
const REFERENCE = {
  sodium:[0.6,0.5,"mEq/L"], potassium:[4.8,2.0,"mEq/L"],
  chloride:[1.2,1.0,"mEq/L"], bicarbonate:[5.5,3.0,"mEq/L"],
  glucose:[5.7,2.5,"mg/dL"], urea:[12.3,3.0,""], creatinine:[5.9,2.2,"mg/dL"],
  calcium:[1.9,1.0,"mg/dL"], magnesium:[3.6,2.0,"mg/dL"],
  phosphate:[8.0,3.0,"mg/dL"], albumin:[3.1,2.0,"g/dL"],
  total_protein:[2.4,2.0,"g/dL"], alt:[19.4,5.0,"U/L"],
  ast:[12.3,5.0,"U/L"], alp:[6.4,4.0,"U/L"],
  total_bilirubin:[23.5,5.0,"mg/dL"], hemoglobin:[2.8,1.5,"g/dL"],
  hematocrit:[3.0,1.5,"%"], wbc:[9.6,3.0,"10^3/uL"],
  platelets:[9.1,4.0,"10^3/uL"], troponin_i:[17.0,10.0,""],
  tsh:[19.7,5.0,""], inr:[4.1,3.0,""],
  crp:[44.0,6.0,""], amylase:[8.6,4.0,"U/L"], lactate:[11.5,4.0,"mmol/L"]
};

/* Fixed thresholds match delta_check/analyzer.py. Either threshold can flag. */
const FIXED = {
  sodium:[4,3], potassium:[0.5,15], glucose:[30,20],
  hemoglobin:[1.5,10], creatinine:[0.3,15], calcium:[0.5,5],
  chloride:[5,5], bicarbonate:[4,10], wbc:[3,20],
  platelets:[50,20], albumin:[0.5,10], total_protein:[0.5,10],
  ast:[20,30], alt:[20,30], total_bilirubin:[1,30], urea:[5,20]
};
const ALIASES = {bun:"urea",co2:"bicarbonate",bilirubin:"total_bilirubin"};

function calculate(data) {
  const analyte = ALIASES[data.analyte] || data.analyte;
  const prior = Number(data.prior);
  const current = Number(data.current);
  const cvi = Number(data.cvi);
  const cva = Number(data.cva);
  const confidence = Number(data.confidence);
  const method = data.method;
  if (!Object.prototype.hasOwnProperty.call(REFERENCE, analyte)) {
    throw new Error("Choose a supported analyte.");
  }
  if (![prior,current,cvi,cva].every(Number.isFinite)) {
    throw new Error("All measurements and coefficients must be finite numbers.");
  }
  if (cvi < 0 || cva < 0) {
    throw new Error("CVi and CVa cannot be negative.");
  }
  if (confidence !== 0.95 && confidence !== 0.99) {
    throw new Error("Confidence must be 95% or 99%.");
  }
  if (!["fixed","rcv","both"].includes(method)) {
    throw new Error("Choose a valid check method.");
  }
  const absDelta = Math.abs(current - prior);
  const pctDelta = prior === 0 ? null : absDelta / Math.abs(prior) * 100;
  const fixedLimits = FIXED[analyte] || null;
  const fixed = method === "fixed" || method === "both";
  const rcv = method === "rcv" || method === "both";
  const fixedFlag = fixed && fixedLimits ?
    (absDelta > fixedLimits[0] || (pctDelta !== null && pctDelta > fixedLimits[1])) : null;
  const rcvThreshold = rcv && prior !== 0 ?
    Math.SQRT2 * (confidence === 0.95 ? 1.96 : 2.576) * Math.hypot(cvi,cva) : null;
  const rcvFlag = rcvThreshold === null ? null : pctDelta > rcvThreshold;
  const available = [fixedFlag,rcvFlag].filter(x => x !== null);
  const flagged = available.length ? available.some(Boolean) : null;
  const complete = (!fixed || fixedFlag !== null) && (!rcv || rcvFlag !== null);
  return {analyte,prior,current,cvi,cva,confidence,method,absDelta,pctDelta,
    fixedLimits,fixedFlag,rcvThreshold,rcvFlag,flagged,complete};
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {calculate,REFERENCE,FIXED};
}

if (typeof document !== "undefined") {
  const $ = id => document.getElementById(id);
  const select = $("analyte");
  Object.keys(REFERENCE).forEach(name => {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name.replaceAll("_"," ");
    select.appendChild(option);
  });
  select.value = "sodium";

  let latest = null;
  const format = n => Number(n).toLocaleString(undefined,{maximumFractionDigits:3});
  function syncReference() {
    const ref = REFERENCE[select.value];
    $("cvi").value = ref[0];
    $("cva").value = ref[1];
    $("unit").textContent = ref[2] || "Confirm units locally";
    $("fixed-note").textContent = FIXED[select.value] ?
      "Fixed-limit and RCV methods available." :
      "RCV only: no fixed limits are defined for this analyte.";
  }
  function render(result) {
    const status = $("status");
    const summary = $("summary");
    const details = $("details");
    status.className = "status " +
      (result.flagged === null ? "partial" : result.flagged ? "flagged" : "clear");
    status.textContent = result.flagged === null ? "NOT EVALUATED" :
      result.flagged ? "DELTA FLAG" : result.complete ? "NO DELTA FLAG" : "PARTIAL CHECK";
    summary.textContent = result.complete ?
      "Compare with locally validated limits and clinical context." :
      "One or more requested methods could not be evaluated; do not treat this as a pass.";
    const rows = [
      ["Absolute change",format(result.absDelta)+" "+($("unit").textContent || "")],
      ["Percent change",result.pctDelta === null ? "Undefined (prior is zero)" : format(result.pctDelta)+"%"]
    ];
    if (result.method !== "rcv") {
      rows.push(["Fixed limits",result.fixedLimits ?
        format(result.fixedLimits[0])+" absolute OR "+format(result.fixedLimits[1])+"%" :
        "Not configured"]);
      rows.push(["Fixed result",result.fixedFlag === null ? "Not evaluated" :
        result.fixedFlag ? "Exceeded" : "Within limits"]);
    }
    if (result.method !== "fixed") {
      rows.push(["RCV threshold",result.rcvThreshold === null ? "Undefined (prior is zero)" :
        format(result.rcvThreshold)+"% at "+(result.confidence*100).toFixed(0)+"%"]);
      rows.push(["RCV result",result.rcvFlag === null ? "Not evaluated" :
        result.rcvFlag ? "Exceeded" : "Within limits"]);
    }
    details.replaceChildren();
    rows.forEach(pair => {
      const dt = document.createElement("dt");
      const dd = document.createElement("dd");
      dt.textContent = pair[0]; dd.textContent = pair[1];
      details.append(dt,dd);
    });
    $("result").hidden = false;
    $("export").disabled = false;
  }
  $("calculator").addEventListener("submit",event => {
    event.preventDefault();
    $("error").textContent = "";
    $("result").hidden = true;
    $("export").disabled = true;
    latest = null;
    try {
      const fields = ["analyte","prior","current","cvi","cva","confidence","method"];
      const values = {};
      fields.forEach(name => { values[name] = $(name).value; });
      if (!["prior","current","cvi","cva"].every(name => $(name).value.trim() !== "")) {
        throw new Error("Complete all numeric inputs.");
      }
      latest = calculate(values);
      render(latest);
    } catch (error) {
      $("error").textContent = error.message;
    }
  });
  $("export").addEventListener("click", () => {
    if (!latest) return;
    const names = ["analyte","prior","current","cvi","cva","confidence","method",
      "absDelta","pctDelta","fixedFlag","rcvThreshold","rcvFlag","flagged","complete"];
    const escapeCsv = v => {
      const s = v === null ? "" : String(v);
      return '"' + s.replaceAll('"','""') + '"';
    };
    const csv = names.join(",")+"\n"+names.map(k=>escapeCsv(latest[k])).join(",")+"\n";
    const url = URL.createObjectURL(new Blob([csv],{type:"text/csv;charset=utf-8"}));
    const a = document.createElement("a");
    a.href = url; a.download = "delta-check-result.csv";
    a.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  select.addEventListener("change",syncReference);
  syncReference();
}
