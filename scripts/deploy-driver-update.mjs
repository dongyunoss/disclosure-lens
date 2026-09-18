// Called only by an explicitly enabled monitor --deploy worker.
import {spawnSync} from 'node:child_process';
import {dirname,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
function run(bin,args,quiet=false){const r=spawnSync(bin,args,{cwd:root,encoding:'utf8',stdio:quiet?'pipe':'inherit'});if(r.error||r.status!==0)throw new Error(bin+' failed');return (r.stdout||'').trimEnd();}
if(run('git',['branch','--show-current'],true)!=='main'||run('git',['remote','get-url','origin'],true)!=='https://github.com/dongyunoss/disclosure-lens.git')throw new Error('Unexpected deployment checkout.');
const changed=run('git',['status','--porcelain','--untracked-files=all'],true).split('\n').filter(Boolean);
if(changed.some(line=>!line.slice(3).replaceAll('"','').startsWith('public/drivers/')))throw new Error('Other work is in progress. Monitor deployment stopped; existing site is retained.');
if(!changed.length)process.exit(0);
run('python',['-m','pipeline.cli','validate-public']);
run('git',['add','--','public/drivers']);
run('git',['commit','-m','Update automatic filing analysis and monitor status']);
run('git',['push','origin','main']);
run('node',['scripts/deploy-pages.mjs']);
