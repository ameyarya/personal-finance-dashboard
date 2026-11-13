// Writes an instrumented copy of public/app.js to .cov/app.js. The tests serve that copy instead of the real file.
const fs = require('fs'), path = require('path');
const { createInstrumenter } = require('istanbul-lib-instrument');
const root = path.resolve(__dirname, '..', '..');
const src = fs.readFileSync(path.join(root, 'public', 'app.js'), 'utf8');
const out = createInstrumenter({ esModules: false, compact: false, produceSourceMap: false, coverageVariable: '__coverage__' }).instrumentSync(src, 'public/app.js');
fs.mkdirSync(path.join(root, '.cov'), { recursive: true });
fs.writeFileSync(path.join(root, '.cov', 'app.js'), out);
