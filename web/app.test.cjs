"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const {calculate,REFERENCE,FIXED} = require("./app.js");

function pair(overrides={}) {
  return calculate({
    analyte:"sodium",prior:140,current:145,cvi:0.6,cva:0.5,
    confidence:0.95,method:"both",...overrides
  });
}

test("reference table covers the Python demonstration analytes",()=>{
  assert.equal(Object.keys(REFERENCE).length,26);
  assert.ok(FIXED.sodium);
});

test("sodium 140 to 145 triggers fixed and RCV",()=>{
  const r=pair();
  assert.equal(r.fixedFlag,true);
  assert.equal(r.rcvFlag,true);
  assert.equal(r.flagged,true);
  assert.ok(Math.abs(r.rcvThreshold - Math.SQRT2*1.96*Math.hypot(0.6,0.5))<1e-12);
});

test("small sodium change is within both thresholds",()=>{
  const r=pair({current:141});
  assert.equal(r.flagged,false);
  assert.equal(r.complete,true);
});

test("99 percent threshold exceeds 95 percent threshold",()=>{
  assert.ok(pair({confidence:0.99}).rcvThreshold > pair().rcvThreshold);
});

test("exact thresholds do not flag",()=>{
  const r=pair({prior:100,current:103,method:"fixed"});
  assert.equal(r.fixedFlag,false);
});

test("zero baseline remains an incomplete check",()=>{
  const r=pair({prior:0,current:0});
  assert.equal(r.rcvFlag,null);
  assert.equal(r.complete,false);
});

test("unsupported fixed threshold is not converted to pass",()=>{
  const r=pair({analyte:"tsh",prior:2,current:2.5,cvi:19.7,cva:5.0});
  assert.equal(r.fixedFlag,null);
  assert.equal(r.complete,false);
});

test("reject nonfinite and invalid CV inputs",()=>{
  for(const val of [NaN,Infinity,"",null]) {
    assert.throws(()=>pair({cvi:val}));
  }
  assert.throws(()=>pair({cva:-2}));
  assert.throws(()=>pair({method:"nothing"}));
  assert.throws(()=>pair({confidence:0.9}));
});
