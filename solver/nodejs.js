#!/usr/bin/env node
let crypto = require('crypto');
let argv = process.argv.slice(2);
let prefix = argv[0];
let difficulty = parseInt(argv[1]);
let zeros = '0'.repeat(difficulty)

let isValid = (hexdigest) => {
  let bin = '';
  for (let c of hexdigest)
    bin += c.toString(2).padStart(8, '0');
  return bin.startsWith(zeros);
}

let i = 0;
while (true) {
  let h = crypto.createHash('sha256');
  h.update(prefix + i.toString());
  if (isValid(h.digest())) {
    console.log(i);
    process.exit(0);
  }
  i++;
}
