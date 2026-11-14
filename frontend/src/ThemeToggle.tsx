import {useEffect,useState} from 'react';

export type Theme='dark'|'light';
const KEY='tf_theme';

/** Dark is the default (the amber halftone look); a saved choice wins. */
export function getTheme():Theme{
  const attr=document.documentElement.getAttribute('data-theme');
  if(attr==='light'||attr==='dark')return attr;
  try{const s=localStorage.getItem(KEY);if(s==='light'||s==='dark')return s}catch{/* storage blocked */}
  return 'dark';
}

export function applyTheme(theme:Theme){
  document.documentElement.setAttribute('data-theme',theme);
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content',theme==='dark'?'#01061a':'#f4f7ff');
  try{localStorage.setItem(KEY,theme)}catch{/* storage blocked */}
}

const Sun=()=><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M5.6 18.4L7 17M17 7l1.4-1.4"/></svg>;
const Moon=()=><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5Z"/></svg>;

export default function ThemeToggle({variant}:{variant?:'nav'}={}){
  const[theme,setTheme]=useState<Theme>(getTheme);
  useEffect(()=>{applyTheme(theme)},[theme]);
  const next:Theme=theme==='dark'?'light':'dark';
  return <button type="button" className={'themeToggle'+(variant==='nav'?' navLink':'')} onClick={()=>setTheme(next)} aria-label={`Switch to ${next} theme`} title={`Switch to ${next} theme`}>
    {theme==='dark'?<Sun/>:<Moon/>}<span>{theme==='dark'?'Light theme':'Dark theme'}</span>
  </button>;
}
