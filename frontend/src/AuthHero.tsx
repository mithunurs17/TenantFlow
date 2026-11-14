import {FormEvent,useEffect,useRef,useState} from 'react';
import ThemeToggle from './ThemeToggle';

const VIDEO='https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20261005_182549_18378239-da8f-48a7-9666-d6e0a6a88561.mp4';
const NB=' ';
/** Words inside a sentence are joined with no-break spaces, so the only wrap point is between sentences. */
const sentence=(s:string)=>s.split(' ').join(NB);
const SUB=`${sentence('Isolated workspaces for every team.')} ${sentence('Boards, sprints and billing built in.')}`;

type Props={mail:string;setMail:(v:string)=>void;password:string;setPassword:(v:string)=>void;wsName:string;setWsName:(v:string)=>void;error:string;onAuth:(register:boolean)=>void};

export default function AuthHero({mail,setMail,password,setPassword,wsName,setWsName,error,onAuth}:Props){
  const root=useRef<HTMLElement>(null);
  const video=useRef<HTMLVideoElement>(null);
  const[mode,setMode]=useState<'signup'|'signin'>('signup');
  const signup=mode==='signup';

  // Entrance: once per load, skipped for reduced motion or when Web Animations is missing.
  useEffect(()=>{
    const el=root.current;if(!el)return;
    if(typeof el.animate!=='function'||typeof matchMedia!=='function'||matchMedia('(prefers-reduced-motion:reduce)').matches)return;
    el.classList.add('intro');
    let started=false;const anims:Animation[]=[];
    const failsafe=window.setTimeout(()=>{if(!started)el.classList.remove('intro')},3500);
    const logo=el.querySelector<HTMLElement>('.logo');
    const k=Math.min(1,Math.max(.65,(logo?logo.getBoundingClientRect().height:23.5)/23.5));
    const quint='cubic-bezier(0.22, 1, 0.36, 1)',expo='cubic-bezier(0.16, 1, 0.3, 1)';
    const go=(t:Element|null,from:Keyframe,duration:number,delay:number,easing:string,to:Keyframe={opacity:1,transform:'none'})=>{
      if(t)anims.push(t.animate([from,to],{duration,delay,easing,fill:'both'}));
    };
    const q=(s:string)=>el.querySelector(s);
    const start=()=>{
      if(started)return;started=true;window.clearTimeout(failsafe);
      go(q('.logo'),{opacity:0,transform:`translateY(${-6*k}px)`},900,60,quint);
      go(q('.rule'),{transform:'scaleX(0)'},1000,180,'cubic-bezier(0.7, 0, 0.2, 1)',{transform:'scaleX(1)'});
      el.querySelectorAll('.heroNav>*').forEach((n,i)=>go(n,{opacity:0,transform:`translateY(${-4*k}px)`},700,i===1?420:490,quint));
      el.querySelectorAll('.l .li').forEach((n,i)=>go(n,{transform:'translateY(104%)'},1100,200+i*90,expo,{transform:'none'}));
      go(q('.sub'),{opacity:0,transform:`translateY(${10*k}px)`},850,700,quint);
      go(q('.authForm'),{opacity:0,transform:`translateY(${12*k}px)`},900,800,expo);
      go(q('.cta'),{opacity:0,transform:`translateY(${12*k}px) scale(.975)`},900,860,expo);
      go(q('.discover'),{opacity:0,transform:`translateY(${6*k}px)`},700,1040,quint);
      go(q('.discover svg'),{transform:`translateY(${-5*k}px)`},820,1120,expo,{transform:'none'});
      Promise.all(anims.map(a=>a.finished)).then(()=>{
        el.classList.remove('intro');anims.forEach(a=>a.cancel());
        // Toggle display once so the masks don't leave a separate GPU layer behind.
        if(!el.contains(document.activeElement)){el.style.display='none';void el.offsetHeight;el.style.display=''}
        document.documentElement.dataset.intro='done';
      }).catch(()=>{});
    };
    const v=video.current;
    const loaded=new Promise<void>(r=>{if(!v||v.readyState>=2)r();else v.addEventListener('loadeddata',()=>r(),{once:true})});
    const fonts=(document.fonts&&document.fonts.ready)||Promise.resolve();
    Promise.race([Promise.all([fonts,loaded]),new Promise(r=>window.setTimeout(r,900))]).then(start);
    return()=>{window.clearTimeout(failsafe);anims.forEach(a=>a.cancel());el.classList.remove('intro')};
  },[]);

  useEffect(()=>{if(video.current)video.current.muted=true},[]);
  const submit=(e:FormEvent)=>{e.preventDefault();onAuth(signup)};
  const pick=(m:'signup'|'signin')=>(e:{preventDefault:()=>void})=>{e.preventDefault();setMode(m)};

  return <main className="hero" ref={root}>
    <header className="mast">
      <a className="logo" href="#" aria-label="TenantFlow home" onClick={e=>e.preventDefault()}>TenantFlow</a>
      <div className="rule"/>
      <nav className="heroNav" aria-label="Primary">
        <a href="#signin" onClick={pick('signin')}>Sign in</a>
        <a href="#signup" onClick={pick('signup')}>Create workspace</a>
        <ThemeToggle variant="nav"/>
      </nav>
    </header>
    <div className="gap"/>
    <section className="copy">
      <h1 className="headline">
        <span className="l"><span className="li">Your team’s work,</span></span>
        <span className="l l2"><span className="li">planned together.</span></span>
      </h1>
      <p className="sub">{SUB}</p>
      <form className="authForm" onSubmit={submit} aria-label={signup?'Create workspace':'Sign in'}>
        <input aria-label="Work email" placeholder="Work email" type="email" autoComplete="email" value={mail} onChange={e=>setMail(e.target.value)}/>
        <input aria-label="Password" placeholder="Password (10+ characters)" type="password" autoComplete={signup?'new-password':'current-password'} value={password} onChange={e=>setPassword(e.target.value)}/>
        {signup&&<input aria-label="Workspace name" placeholder="Workspace name" value={wsName} onChange={e=>setWsName(e.target.value)}/>}
        {error&&<p className="error" role="alert">{error}</p>}
        <button className="cta" type="submit">{signup?'Create workspace':'Sign in'}</button>
      </form>
      <a className="discover" href="#" onClick={pick(signup?'signin':'signup')}>{signup?'I already have an account':'Create a new workspace'}
        <svg viewBox="0 0 11 12.6" aria-hidden="true"><path d="M5.5 .4V12M1 7.5L5.5 12L10 7.5"/></svg></a>
    </section>
    <div className="field"><video ref={video} autoPlay muted loop playsInline preload="auto" aria-hidden="true" tabIndex={-1} disablePictureInPicture src={VIDEO}/></div>
  </main>;
}
