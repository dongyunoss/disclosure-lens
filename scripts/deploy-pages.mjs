import {spawnSync} from 'node:child_process';
import {mkdtempSync,cpSync,readdirSync,rmSync,writeFileSync} from 'node:fs';
import {resolve,join,sep,dirname} from 'node:path';
import {tmpdir} from 'node:os';
import {fileURLToPath} from 'node:url';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
function run(bin,args,cwd=root,quiet=false){
 const result=spawnSync(bin,args,{cwd,encoding:'utf8',stdio:quiet?'pipe':'inherit',shell:false});
 if(result.error||result.status!==0)throw new Error(quiet?String(result.stderr||result.error):bin+' failed');
 return (result.stdout||'').trim();
}
function npmRun(task){
 if(process.platform==='win32')return run('cmd.exe',['/d','/s','/c','npm.cmd run '+task]);
 return run('npm',['run',task]);
}
if(run('git',['status','--porcelain'],root,true))throw new Error('Commit source changes before deployment.');
run('python',['-m','unittest','discover','-s','tests']);
run('python',['-m','pipeline.cli','validate-public']);
npmRun('test');npmRun('test:browser');npmRun('build');
const repo=run('git',['remote','get-url','origin'],root,true);
if(repo!=='https://github.com/dongyunoss/disclosure-lens.git')throw new Error('Unexpected deployment repository.');
const head=run('git',['rev-parse','HEAD'],root,true);
const folder=mkdtempSync(join(tmpdir(),'disclosure-pages-'));
const remote=run('git',['ls-remote','--heads',repo,'gh-pages'],root,true);
if(remote)run('git',['clone','--depth','1','--branch','gh-pages',repo,folder]);
else{run('git',['init','-b','gh-pages'],folder);run('git',['remote','add','origin',repo],folder);}
for(const entry of readdirSync(folder,{withFileTypes:true})){
 if(entry.name==='.git')continue;
 const target=resolve(folder,entry.name);
 if(!target.startsWith(resolve(folder)+sep))throw new Error('Invalid temporary cleanup target');
 rmSync(target,{recursive:true,force:true});
}
cpSync(join(root,'dist'),folder,{recursive:true});
writeFileSync(join(folder,'.nojekyll'),'');
writeFileSync(join(folder,'release.json'),JSON.stringify({sourceCommit:head,deployedAt:new Date().toISOString()}));
run('git',['add','--all'],folder);
run('git',['commit','-m','Deploy validated source '+head.slice(0,12)],folder);
run('git',['push','origin','HEAD:gh-pages'],folder);
console.log('Published validated static files. GitHub Pages will complete deployment.');
