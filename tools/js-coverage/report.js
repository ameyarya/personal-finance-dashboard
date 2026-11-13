// Reads js-coverage.json (merged by the tests) and prints how much of public/app.js ran. --list shows every piece that never did.
const fs = require('fs'), path = require('path');
const libCoverage = require('istanbul-lib-coverage'), libReport = require('istanbul-lib-report'), reports = require('istanbul-reports');
const root = path.resolve(__dirname, '..', '..');
const file = path.join(root, 'js-coverage.json');
if (!fs.existsSync(file)) { console.log('no js-coverage.json: run the tests with JS_COVERAGE=1 (tools/coverage.sh does)'); process.exit(1); }
const map = libCoverage.createCoverageMap(JSON.parse(fs.readFileSync(file, 'utf8')));
const context = libReport.createContext({ dir: path.join(root, 'htmlcov-js'), coverageMap: map });
reports.create('text').execute(context);
if (process.argv.includes('--html')) reports.create('html').execute(context);
const src = fs.readFileSync(path.join(root, 'public', 'app.js'), 'utf8').split('\n');
const fc = map.fileCoverageFor(map.files()[0]).toJSON();
const gaps = [];
const snippet = (loc) => (src[loc.start.line - 1] || '').slice(Math.max(0, loc.start.column - 5), loc.start.column + 110).trim();
for (const [id, n] of Object.entries(fc.s)) if (!n) gaps.push(['statement', fc.statementMap[id].start, snippet(fc.statementMap[id])]);
for (const [id, counts] of Object.entries(fc.b)) counts.forEach((n, i) => { if (!n) gaps.push(['branch', fc.branchMap[id].locations[i].start, snippet(fc.branchMap[id].locations[i])]); });
for (const [id, n] of Object.entries(fc.f)) if (!n) gaps.push(['function', fc.fnMap[id].loc.start, fc.fnMap[id].name]);
gaps.sort((a, b) => a[1].line - b[1].line || a[1].column - b[1].column);
fs.writeFileSync(path.join(root, 'js-coverage-gaps.txt'), gaps.map(g => `${g[0]}\tline ${g[1].line}:${g[1].column}\t${g[2]}`).join('\n') + '\n');
console.log(gaps.length + ' pieces never ran (see js-coverage-gaps.txt)');
if (process.argv.includes('--list')) gaps.forEach(g => console.log(`  ${g[0]} line ${g[1].line}: ${g[2]}`));
process.exit(gaps.length ? 2 : 0);
