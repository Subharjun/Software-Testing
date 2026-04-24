// @ts-nocheck
// Pa11y accessibility configuration
// Tests the QA Forge frontend against WCAG 2.1 AA standard

module.exports = {
  standard: "WCAG2AA",
  timeout: 30000,
  wait: 2000,
  ignore: [
    "WCAG2AA.Principle1.Guideline1_4.1_4_3.G18.Fail"  // known CSP contrast issue
  ],
  runners: ["axe", "htmlcs"],
  chromeLaunchConfig: {
    args: ["--no-sandbox", "--disable-setuid-sandbox"]
  }
};
