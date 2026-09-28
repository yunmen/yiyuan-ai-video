import{$ as e,B as t,E as n,F as r,G as i,L as a,M as o,O as s,W as c,Z as l,d as u,et as d,h as f,k as p,m,q as h,rt as g,s as _,v}from"./vue-vendor-VvR516j_.js";import{At as y,C as b,D as x,Dt as S,E as C,F as w,Gt as T,Lt as E,O as D,Ot as O,S as k,T as A,Xt as j,Zt as M,_ as N,a as P,b as ee,bn as te,c as ne,dn as F,en as I,ft as re,gn as L,hn as R,in as z,j as B,kt as V,l as H,m as ie,mn as U,mt as W,nn as ae,o as oe,p as se,pn as G,pt as ce,rn as K,tn as le,un as q,vt as ue,w as J,x as Y,y as de,zt as fe}from"./initial-vendor-DGcJKj6B.js";import{g as pe,o as X}from"./Popover-B5gZpOZf.js";import{t as me}from"./use-merged-state-D72VTG8A.js";import{n as he,t as ge}from"./Eye-Czh4ydd5.js";import{a as _e,i as ve,n as ye,r as be,t as xe}from"./Tooltip-BrHnsQiu.js";function Se(e,t){if(!e)return;let n=document.createElement(`a`);n.href=e,t!==void 0&&(n.download=t),document.body.appendChild(n),n.click(),document.body.removeChild(n)}function Ce(e,t,n,r){var i=-1,a=e==null?0:e.length;for(r&&a&&(n=e[++i]);++i<a;)n=t(n,e[i],i,e);return n}function we(e){return function(t){return e?.[t]}}var Te=we({À:`A`,Á:`A`,Â:`A`,Ã:`A`,Ä:`A`,Å:`A`,à:`a`,á:`a`,â:`a`,ã:`a`,ä:`a`,å:`a`,Ç:`C`,ç:`c`,Ð:`D`,ð:`d`,È:`E`,É:`E`,Ê:`E`,Ë:`E`,è:`e`,é:`e`,ê:`e`,ë:`e`,Ì:`I`,Í:`I`,Î:`I`,Ï:`I`,ì:`i`,í:`i`,î:`i`,ï:`i`,Ñ:`N`,ñ:`n`,Ò:`O`,Ó:`O`,Ô:`O`,Õ:`O`,Ö:`O`,Ø:`O`,ò:`o`,ó:`o`,ô:`o`,õ:`o`,ö:`o`,ø:`o`,Ù:`U`,Ú:`U`,Û:`U`,Ü:`U`,ù:`u`,ú:`u`,û:`u`,ü:`u`,Ý:`Y`,ý:`y`,ÿ:`y`,Æ:`Ae`,æ:`ae`,Þ:`Th`,þ:`th`,ß:`ss`,Ā:`A`,Ă:`A`,Ą:`A`,ā:`a`,ă:`a`,ą:`a`,Ć:`C`,Ĉ:`C`,Ċ:`C`,Č:`C`,ć:`c`,ĉ:`c`,ċ:`c`,č:`c`,Ď:`D`,Đ:`D`,ď:`d`,đ:`d`,Ē:`E`,Ĕ:`E`,Ė:`E`,Ę:`E`,Ě:`E`,ē:`e`,ĕ:`e`,ė:`e`,ę:`e`,ě:`e`,Ĝ:`G`,Ğ:`G`,Ġ:`G`,Ģ:`G`,ĝ:`g`,ğ:`g`,ġ:`g`,ģ:`g`,Ĥ:`H`,Ħ:`H`,ĥ:`h`,ħ:`h`,Ĩ:`I`,Ī:`I`,Ĭ:`I`,Į:`I`,İ:`I`,ĩ:`i`,ī:`i`,ĭ:`i`,į:`i`,ı:`i`,Ĵ:`J`,ĵ:`j`,Ķ:`K`,ķ:`k`,ĸ:`k`,Ĺ:`L`,Ļ:`L`,Ľ:`L`,Ŀ:`L`,Ł:`L`,ĺ:`l`,ļ:`l`,ľ:`l`,ŀ:`l`,ł:`l`,Ń:`N`,Ņ:`N`,Ň:`N`,Ŋ:`N`,ń:`n`,ņ:`n`,ň:`n`,ŋ:`n`,Ō:`O`,Ŏ:`O`,Ő:`O`,ō:`o`,ŏ:`o`,ő:`o`,Ŕ:`R`,Ŗ:`R`,Ř:`R`,ŕ:`r`,ŗ:`r`,ř:`r`,Ś:`S`,Ŝ:`S`,Ş:`S`,Š:`S`,ś:`s`,ŝ:`s`,ş:`s`,š:`s`,Ţ:`T`,Ť:`T`,Ŧ:`T`,ţ:`t`,ť:`t`,ŧ:`t`,Ũ:`U`,Ū:`U`,Ŭ:`U`,Ů:`U`,Ű:`U`,Ų:`U`,ũ:`u`,ū:`u`,ŭ:`u`,ů:`u`,ű:`u`,ų:`u`,Ŵ:`W`,ŵ:`w`,Ŷ:`Y`,ŷ:`y`,Ÿ:`Y`,Ź:`Z`,Ż:`Z`,Ž:`Z`,ź:`z`,ż:`z`,ž:`z`,Ĳ:`IJ`,ĳ:`ij`,Œ:`Oe`,œ:`oe`,ŉ:`'n`,ſ:`s`}),Ee=/[\xc0-\xd6\xd8-\xf6\xf8-\xff\u0100-\u017f]/g,De=RegExp(`[\\u0300-\\u036f\\ufe20-\\ufe2f\\u20d0-\\u20ff]`,`g`);function Oe(e){return e=w(e),e&&e.replace(Ee,Te).replace(De,``)}var ke=/[^\x00-\x2f\x3a-\x40\x5b-\x60\x7b-\x7f]+/g;function Ae(e){return e.match(ke)||[]}var je=/[a-z][A-Z]|[A-Z]{2}[a-z]|[0-9][a-zA-Z]|[a-zA-Z][0-9]|[^a-zA-Z0-9 ]/;function Me(e){return je.test(e)}var Ne=`\\ud800-\\udfff`,Pe=`\\u0300-\\u036f\\ufe20-\\ufe2f\\u20d0-\\u20ff`,Fe=`\\u2700-\\u27bf`,Ie=`a-z\\xdf-\\xf6\\xf8-\\xff`,Le=`\\xac\\xb1\\xd7\\xf7`,Re=`\\x00-\\x2f\\x3a-\\x40\\x5b-\\x60\\x7b-\\xbf`,ze=`\\u2000-\\u206f`,Be=` \\t\\x0b\\f\\xa0\\ufeff\\n\\r\\u2028\\u2029\\u1680\\u180e\\u2000\\u2001\\u2002\\u2003\\u2004\\u2005\\u2006\\u2007\\u2008\\u2009\\u200a\\u202f\\u205f\\u3000`,Ve=`A-Z\\xc0-\\xd6\\xd8-\\xde`,He=`\\ufe0e\\ufe0f`,Ue=Le+Re+ze+Be,We=`['’]`,Ge=`[`+Ue+`]`,Ke=`[`+Pe+`]`,qe=`\\d+`,Je=`[`+Fe+`]`,Ye=`[`+Ie+`]`,Xe=`[^`+Ne+Ue+qe+Fe+Ie+Ve+`]`,Ze=`(?:`+Ke+`|\\ud83c[\\udffb-\\udfff])`,Qe=`[^`+Ne+`]`,$e=`(?:\\ud83c[\\udde6-\\uddff]){2}`,et=`[\\ud800-\\udbff][\\udc00-\\udfff]`,Z=`[`+Ve+`]`,tt=`\\u200d`,nt=`(?:`+Ye+`|`+Xe+`)`,rt=`(?:`+Z+`|`+Xe+`)`,it=`(?:`+We+`(?:d|ll|m|re|s|t|ve))?`,at=`(?:`+We+`(?:D|LL|M|RE|S|T|VE))?`,ot=Ze+`?`,st=`[`+He+`]?`,ct=`(?:`+tt+`(?:`+[Qe,$e,et].join(`|`)+`)`+st+ot+`)*`,lt=`\\d*(?:1st|2nd|3rd|(?![123])\\dth)(?=\\b|[A-Z_])`,ut=`\\d*(?:1ST|2ND|3RD|(?![123])\\dTH)(?=\\b|[a-z_])`,dt=st+ot+ct,ft=`(?:`+[Je,$e,et].join(`|`)+`)`+dt,pt=RegExp([Z+`?`+Ye+`+`+it+`(?=`+[Ge,Z,`$`].join(`|`)+`)`,rt+`+`+at+`(?=`+[Ge,Z+nt,`$`].join(`|`)+`)`,Z+`?`+nt+`+`+it,Z+`+`+at,ut,lt,qe,ft].join(`|`),`g`);function mt(e){return e.match(pt)||[]}function ht(e,t,n){return e=w(e),t=n?void 0:t,t===void 0?Me(e)?mt(e):Ae(e):e.match(t)||[]}var gt=RegExp(`['’]`,`g`);function _t(e){return function(t){return Ce(ht(Oe(t).replace(gt,``)),e,``)}}var vt=_t(function(e,t,n){return e+(n?`-`:``)+t.toLowerCase()}),yt=J(`attach`,()=>s(`svg`,{viewBox:`0 0 16 16`,version:`1.1`,xmlns:`http://www.w3.org/2000/svg`},s(`g`,{stroke:`none`,"stroke-width":`1`,fill:`none`,"fill-rule":`evenodd`},s(`g`,{fill:`currentColor`,"fill-rule":`nonzero`},s(`path`,{d:`M3.25735931,8.70710678 L7.85355339,4.1109127 C8.82986412,3.13460197 10.4127766,3.13460197 11.3890873,4.1109127 C12.365398,5.08722343 12.365398,6.67013588 11.3890873,7.64644661 L6.08578644,12.9497475 C5.69526215,13.3402718 5.06209717,13.3402718 4.67157288,12.9497475 C4.28104858,12.5592232 4.28104858,11.9260582 4.67157288,11.5355339 L9.97487373,6.23223305 C10.1701359,6.0369709 10.1701359,5.72038841 9.97487373,5.52512627 C9.77961159,5.32986412 9.4630291,5.32986412 9.26776695,5.52512627 L3.96446609,10.8284271 C3.18341751,11.6094757 3.18341751,12.8758057 3.96446609,13.6568542 C4.74551468,14.4379028 6.01184464,14.4379028 6.79289322,13.6568542 L12.0961941,8.35355339 C13.4630291,6.98671837 13.4630291,4.77064094 12.0961941,3.40380592 C10.7293591,2.0369709 8.51328163,2.0369709 7.14644661,3.40380592 L2.55025253,8 C2.35499039,8.19526215 2.35499039,8.51184464 2.55025253,8.70710678 C2.74551468,8.90236893 3.06209717,8.90236893 3.25735931,8.70710678 Z`}))))),bt=J(`cancel`,()=>s(`svg`,{viewBox:`0 0 16 16`,version:`1.1`,xmlns:`http://www.w3.org/2000/svg`},s(`g`,{stroke:`none`,"stroke-width":`1`,fill:`none`,"fill-rule":`evenodd`},s(`g`,{fill:`currentColor`,"fill-rule":`nonzero`},s(`path`,{d:`M2.58859116,2.7156945 L2.64644661,2.64644661 C2.82001296,2.47288026 3.08943736,2.45359511 3.2843055,2.58859116 L3.35355339,2.64644661 L8,7.293 L12.6464466,2.64644661 C12.8417088,2.45118446 13.1582912,2.45118446 13.3535534,2.64644661 C13.5488155,2.84170876 13.5488155,3.15829124 13.3535534,3.35355339 L8.707,8 L13.3535534,12.6464466 C13.5271197,12.820013 13.5464049,13.0894374 13.4114088,13.2843055 L13.3535534,13.3535534 C13.179987,13.5271197 12.9105626,13.5464049 12.7156945,13.4114088 L12.6464466,13.3535534 L8,8.707 L3.35355339,13.3535534 C3.15829124,13.5488155 2.84170876,13.5488155 2.64644661,13.3535534 C2.45118446,13.1582912 2.45118446,12.8417088 2.64644661,12.6464466 L7.293,8 L2.64644661,3.35355339 C2.47288026,3.17998704 2.45359511,2.91056264 2.58859116,2.7156945 L2.64644661,2.64644661 L2.58859116,2.7156945 Z`}))))),xt=J(`download`,()=>s(`svg`,{viewBox:`0 0 16 16`,version:`1.1`,xmlns:`http://www.w3.org/2000/svg`},s(`g`,{stroke:`none`,"stroke-width":`1`,fill:`none`,"fill-rule":`evenodd`},s(`g`,{fill:`currentColor`,"fill-rule":`nonzero`},s(`path`,{d:`M3.5,13 L12.5,13 C12.7761424,13 13,13.2238576 13,13.5 C13,13.7454599 12.8231248,13.9496084 12.5898756,13.9919443 L12.5,14 L3.5,14 C3.22385763,14 3,13.7761424 3,13.5 C3,13.2545401 3.17687516,13.0503916 3.41012437,13.0080557 L3.5,13 L12.5,13 L3.5,13 Z M7.91012437,1.00805567 L8,1 C8.24545989,1 8.44960837,1.17687516 8.49194433,1.41012437 L8.5,1.5 L8.5,10.292 L11.1819805,7.6109127 C11.3555469,7.43734635 11.6249713,7.4180612 11.8198394,7.55305725 L11.8890873,7.6109127 C12.0626536,7.78447906 12.0819388,8.05390346 11.9469427,8.2487716 L11.8890873,8.31801948 L8.35355339,11.8535534 C8.17998704,12.0271197 7.91056264,12.0464049 7.7156945,11.9114088 L7.64644661,11.8535534 L4.1109127,8.31801948 C3.91565056,8.12275734 3.91565056,7.80617485 4.1109127,7.6109127 C4.28447906,7.43734635 4.55390346,7.4180612 4.7487716,7.55305725 L4.81801948,7.6109127 L7.5,10.292 L7.5,1.5 C7.5,1.25454011 7.67687516,1.05039163 7.91012437,1.00805567 L8,1 L7.91012437,1.00805567 Z`}))))),St=n({name:`ResizeSmall`,render(){return s(`svg`,{xmlns:`http://www.w3.org/2000/svg`,viewBox:`0 0 20 20`},s(`g`,{fill:`none`},s(`path`,{d:`M5.5 4A1.5 1.5 0 0 0 4 5.5v1a.5.5 0 0 1-1 0v-1A2.5 2.5 0 0 1 5.5 3h1a.5.5 0 0 1 0 1h-1zM16 5.5A1.5 1.5 0 0 0 14.5 4h-1a.5.5 0 0 1 0-1h1A2.5 2.5 0 0 1 17 5.5v1a.5.5 0 0 1-1 0v-1zm0 9a1.5 1.5 0 0 1-1.5 1.5h-1a.5.5 0 0 0 0 1h1a2.5 2.5 0 0 0 2.5-2.5v-1a.5.5 0 0 0-1 0v1zm-12 0A1.5 1.5 0 0 0 5.5 16h1.25a.5.5 0 0 1 0 1H5.5A2.5 2.5 0 0 1 3 14.5v-1.25a.5.5 0 0 1 1 0v1.25zM8.5 7A1.5 1.5 0 0 0 7 8.5v3A1.5 1.5 0 0 0 8.5 13h3a1.5 1.5 0 0 0 1.5-1.5v-3A1.5 1.5 0 0 0 11.5 7h-3zM8 8.5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 .5.5v3a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-3z`,fill:`currentColor`})))}}),Ct=J(`retry`,()=>s(`svg`,{xmlns:`http://www.w3.org/2000/svg`,viewBox:`0 0 512 512`},s(`path`,{d:`M320,146s24.36-12-64-12A160,160,0,1,0,416,294`,style:`fill: none; stroke: currentcolor; stroke-linecap: round; stroke-miterlimit: 10; stroke-width: 32px;`}),s(`polyline`,{points:`256 58 336 138 256 218`,style:`fill: none; stroke: currentcolor; stroke-linecap: round; stroke-linejoin: round; stroke-width: 32px;`}))),wt=J(`rotateClockwise`,()=>s(`svg`,{viewBox:`0 0 20 20`,fill:`none`,xmlns:`http://www.w3.org/2000/svg`},s(`path`,{d:`M3 10C3 6.13401 6.13401 3 10 3C13.866 3 17 6.13401 17 10C17 12.7916 15.3658 15.2026 13 16.3265V14.5C13 14.2239 12.7761 14 12.5 14C12.2239 14 12 14.2239 12 14.5V17.5C12 17.7761 12.2239 18 12.5 18H15.5C15.7761 18 16 17.7761 16 17.5C16 17.2239 15.7761 17 15.5 17H13.8758C16.3346 15.6357 18 13.0128 18 10C18 5.58172 14.4183 2 10 2C5.58172 2 2 5.58172 2 10C2 10.2761 2.22386 10.5 2.5 10.5C2.77614 10.5 3 10.2761 3 10Z`,fill:`currentColor`}),s(`path`,{d:`M10 12C11.1046 12 12 11.1046 12 10C12 8.89543 11.1046 8 10 8C8.89543 8 8 8.89543 8 10C8 11.1046 8.89543 12 10 12ZM10 11C9.44772 11 9 10.5523 9 10C9 9.44772 9.44772 9 10 9C10.5523 9 11 9.44772 11 10C11 10.5523 10.5523 11 10 11Z`,fill:`currentColor`}))),Tt=J(`rotateClockwise`,()=>s(`svg`,{viewBox:`0 0 20 20`,fill:`none`,xmlns:`http://www.w3.org/2000/svg`},s(`path`,{d:`M17 10C17 6.13401 13.866 3 10 3C6.13401 3 3 6.13401 3 10C3 12.7916 4.63419 15.2026 7 16.3265V14.5C7 14.2239 7.22386 14 7.5 14C7.77614 14 8 14.2239 8 14.5V17.5C8 17.7761 7.77614 18 7.5 18H4.5C4.22386 18 4 17.7761 4 17.5C4 17.2239 4.22386 17 4.5 17H6.12422C3.66539 15.6357 2 13.0128 2 10C2 5.58172 5.58172 2 10 2C14.4183 2 18 5.58172 18 10C18 10.2761 17.7761 10.5 17.5 10.5C17.2239 10.5 17 10.2761 17 10Z`,fill:`currentColor`}),s(`path`,{d:`M10 12C8.89543 12 8 11.1046 8 10C8 8.89543 8.89543 8 10 8C11.1046 8 12 8.89543 12 10C12 11.1046 11.1046 12 10 12ZM10 11C10.5523 11 11 10.5523 11 10C11 9.44772 10.5523 9 10 9C9.44772 9 9 9.44772 9 10C9 10.5523 9.44772 11 10 11Z`,fill:`currentColor`}))),Et=J(`trash`,()=>s(`svg`,{xmlns:`http://www.w3.org/2000/svg`,viewBox:`0 0 512 512`},s(`path`,{d:`M432,144,403.33,419.74A32,32,0,0,1,371.55,448H140.46a32,32,0,0,1-31.78-28.26L80,144`,style:`fill: none; stroke: currentcolor; stroke-linecap: round; stroke-linejoin: round; stroke-width: 32px;`}),s(`rect`,{x:`32`,y:`64`,width:`448`,height:`80`,rx:`16`,ry:`16`,style:`fill: none; stroke: currentcolor; stroke-linecap: round; stroke-linejoin: round; stroke-width: 32px;`}),s(`line`,{x1:`312`,y1:`240`,x2:`200`,y2:`352`,style:`fill: none; stroke: currentcolor; stroke-linecap: round; stroke-linejoin: round; stroke-width: 32px;`}),s(`line`,{x1:`312`,y1:`352`,x2:`200`,y2:`240`,style:`fill: none; stroke: currentcolor; stroke-linecap: round; stroke-linejoin: round; stroke-width: 32px;`}))),Dt=J(`zoomIn`,()=>s(`svg`,{viewBox:`0 0 20 20`,fill:`none`,xmlns:`http://www.w3.org/2000/svg`},s(`path`,{d:`M11.5 8.5C11.5 8.22386 11.2761 8 11 8H9V6C9 5.72386 8.77614 5.5 8.5 5.5C8.22386 5.5 8 5.72386 8 6V8H6C5.72386 8 5.5 8.22386 5.5 8.5C5.5 8.77614 5.72386 9 6 9H8V11C8 11.2761 8.22386 11.5 8.5 11.5C8.77614 11.5 9 11.2761 9 11V9H11C11.2761 9 11.5 8.77614 11.5 8.5Z`,fill:`currentColor`}),s(`path`,{d:`M8.5 3C11.5376 3 14 5.46243 14 8.5C14 9.83879 13.5217 11.0659 12.7266 12.0196L16.8536 16.1464C17.0488 16.3417 17.0488 16.6583 16.8536 16.8536C16.68 17.0271 16.4106 17.0464 16.2157 16.9114L16.1464 16.8536L12.0196 12.7266C11.0659 13.5217 9.83879 14 8.5 14C5.46243 14 3 11.5376 3 8.5C3 5.46243 5.46243 3 8.5 3ZM8.5 4C6.01472 4 4 6.01472 4 8.5C4 10.9853 6.01472 13 8.5 13C10.9853 13 13 10.9853 13 8.5C13 6.01472 10.9853 4 8.5 4Z`,fill:`currentColor`}))),Ot=J(`zoomOut`,()=>s(`svg`,{viewBox:`0 0 20 20`,fill:`none`,xmlns:`http://www.w3.org/2000/svg`},s(`path`,{d:`M11 8C11.2761 8 11.5 8.22386 11.5 8.5C11.5 8.77614 11.2761 9 11 9H6C5.72386 9 5.5 8.77614 5.5 8.5C5.5 8.22386 5.72386 8 6 8H11Z`,fill:`currentColor`}),s(`path`,{d:`M14 8.5C14 5.46243 11.5376 3 8.5 3C5.46243 3 3 5.46243 3 8.5C3 11.5376 5.46243 14 8.5 14C9.83879 14 11.0659 13.5217 12.0196 12.7266L16.1464 16.8536L16.2157 16.9114C16.4106 17.0464 16.68 17.0271 16.8536 16.8536C17.0488 16.6583 17.0488 16.3417 16.8536 16.1464L12.7266 12.0196C13.5217 11.0659 14 9.83879 14 8.5ZM4 8.5C4 6.01472 6.01472 4 8.5 4C10.9853 4 13 6.01472 13 8.5C13 10.9853 10.9853 13 8.5 13C6.01472 13 4 10.9853 4 8.5Z`,fill:`currentColor`})));function kt(e){let{infoColor:t,successColor:n,warningColor:r,errorColor:i,textColor2:a,progressRailColor:o,fontSize:s,fontWeight:c}=e;return{fontSize:s,fontSizeCircle:`28px`,fontWeightCircle:c,railColor:o,railHeight:`8px`,iconSizeCircle:`36px`,iconSizeLine:`18px`,iconColor:t,iconColorInfo:t,iconColorSuccess:n,iconColorWarning:r,iconColorError:i,textColorCircle:a,textColorLineInner:`rgb(255, 255, 255)`,textColorLineOuter:a,fillColor:t,fillColorInfo:t,fillColorSuccess:n,fillColorWarning:r,fillColorError:i,lineBgProcessing:`linear-gradient(90deg, rgba(255, 255, 255, .3) 0%, rgba(255, 255, 255, .5) 100%)`}}var At={name:`Progress`,common:se,self:kt};function jt(e){let{iconColor:t,primaryColor:n,errorColor:r,textColor2:i,successColor:a,opacityDisabled:o,actionColor:s,borderColor:c,hoverColor:l,lineHeight:u,borderRadius:d,fontSize:f}=e;return{fontSize:f,lineHeight:u,borderRadius:d,draggerColor:s,draggerBorder:`1px dashed ${c}`,draggerBorderHover:`1px dashed ${n}`,itemColorHover:l,itemColorHoverError:z(r,{alpha:.06}),itemTextColor:i,itemTextColorError:r,itemTextColorSuccess:a,itemIconColor:t,itemDisabledOpacity:o,itemBorderImageCardError:`1px solid ${r}`,itemBorderImageCard:`1px solid ${c}`}}var Mt=x({name:`Upload`,common:se,peers:{Button:oe,Progress:At},self:jt});function Nt(){return{toolbarIconColor:`rgba(255, 255, 255, .9)`,toolbarColor:`rgba(0, 0, 0, .35)`,toolbarBoxShadow:`none`,toolbarBorderRadius:`24px`}}var Pt=x({name:`Image`,common:se,peers:{Tooltip:ye},self:Nt});function Ft(){return s(`svg`,{viewBox:`0 0 20 20`,fill:`none`,xmlns:`http://www.w3.org/2000/svg`},s(`path`,{d:`M6 5C5.75454 5 5.55039 5.17688 5.50806 5.41012L5.5 5.5V14.5C5.5 14.7761 5.72386 15 6 15C6.24546 15 6.44961 14.8231 6.49194 14.5899L6.5 14.5V5.5C6.5 5.22386 6.27614 5 6 5ZM13.8536 5.14645C13.68 4.97288 13.4106 4.9536 13.2157 5.08859L13.1464 5.14645L8.64645 9.64645C8.47288 9.82001 8.4536 10.0894 8.58859 10.2843L8.64645 10.3536L13.1464 14.8536C13.3417 15.0488 13.6583 15.0488 13.8536 14.8536C14.0271 14.68 14.0464 14.4106 13.9114 14.2157L13.8536 14.1464L9.70711 10L13.8536 5.85355C14.0488 5.65829 14.0488 5.34171 13.8536 5.14645Z`,fill:`currentColor`}))}function It(){return s(`svg`,{viewBox:`0 0 20 20`,fill:`none`,xmlns:`http://www.w3.org/2000/svg`},s(`path`,{d:`M13.5 5C13.7455 5 13.9496 5.17688 13.9919 5.41012L14 5.5V14.5C14 14.7761 13.7761 15 13.5 15C13.2545 15 13.0504 14.8231 13.0081 14.5899L13 14.5V5.5C13 5.22386 13.2239 5 13.5 5ZM5.64645 5.14645C5.82001 4.97288 6.08944 4.9536 6.28431 5.08859L6.35355 5.14645L10.8536 9.64645C11.0271 9.82001 11.0464 10.0894 10.9114 10.2843L10.8536 10.3536L6.35355 14.8536C6.15829 15.0488 5.84171 15.0488 5.64645 14.8536C5.47288 14.68 5.4536 14.4106 5.58859 14.2157L5.64645 14.1464L9.79289 10L5.64645 5.85355C5.45118 5.65829 5.45118 5.34171 5.64645 5.14645Z`,fill:`currentColor`}))}function Lt(){return s(`svg`,{viewBox:`0 0 20 20`,fill:`none`,xmlns:`http://www.w3.org/2000/svg`},s(`path`,{d:`M4.089 4.216l.057-.07a.5.5 0 0 1 .638-.057l.07.057L10 9.293l5.146-5.147a.5.5 0 0 1 .638-.057l.07.057a.5.5 0 0 1 .057.638l-.057.07L10.707 10l5.147 5.146a.5.5 0 0 1 .057.638l-.057.07a.5.5 0 0 1-.638.057l-.07-.057L10 10.707l-5.146 5.147a.5.5 0 0 1-.638.057l-.07-.057a.5.5 0 0 1-.057-.638l.057-.07L9.293 10L4.146 4.854a.5.5 0 0 1-.057-.638l.057-.07l-.057.07z`,fill:`currentColor`}))}var Rt=Object.assign(Object.assign({},D.props),{onPreviewPrev:Function,onPreviewNext:Function,showToolbar:{type:Boolean,default:!0},showToolbarTooltip:Boolean,renderToolbar:Function}),zt=j(`n-image`),Bt=q([q(`body >`,[F(`image-container`,`position: fixed;`)]),F(`image-preview-container`,`
 position: fixed;
 left: 0;
 right: 0;
 top: 0;
 bottom: 0;
 display: flex;
 `),F(`image-preview-overlay`,`
 z-index: -1;
 position: absolute;
 left: 0;
 right: 0;
 top: 0;
 bottom: 0;
 background: rgba(0, 0, 0, .3);
 `,[ie()]),F(`image-preview-toolbar`,`
 z-index: 1;
 position: absolute;
 left: 50%;
 transform: translateX(-50%);
 border-radius: var(--n-toolbar-border-radius);
 height: 48px;
 bottom: 40px;
 padding: 0 12px;
 background: var(--n-toolbar-color);
 box-shadow: var(--n-toolbar-box-shadow);
 color: var(--n-toolbar-icon-color);
 transition: color .3s var(--n-bezier);
 display: flex;
 align-items: center;
 `,[F(`base-icon`,`
 padding: 0 8px;
 font-size: 28px;
 cursor: pointer;
 `),ie()]),F(`image-preview-wrapper`,`
 position: absolute;
 left: 0;
 right: 0;
 top: 0;
 bottom: 0;
 display: flex;
 pointer-events: none;
 `,[H()]),F(`image-preview`,`
 user-select: none;
 -webkit-user-select: none;
 pointer-events: all;
 margin: auto;
 max-height: calc(100vh - 32px);
 max-width: calc(100vw - 32px);
 transition: transform .3s var(--n-bezier);
 `),F(`image`,`
 display: inline-flex;
 max-height: 100%;
 max-width: 100%;
 `,[R(`preview-disabled`,`
 cursor: pointer;
 `),q(`img`,`
 border-radius: inherit;
 `)])]),Vt=32,Ht=n({name:`ImagePreview`,props:Object.assign(Object.assign({},Rt),{src:String,show:{type:Boolean,default:void 0},defaultShow:Boolean,"onUpdate:show":[Function,Array],onUpdateShow:[Function,Array],onNext:Function,onPrev:Function,onClose:[Function,Array]}),setup(t){let{src:n}=d(t),{mergedClsPrefixRef:i}=W(t),a=D(`Image`,`-image`,Bt,Pt,t,i),o=null,u=l(null),f=l(null),m=l(!1),{localeRef:h}=he(`Image`),_=l(t.defaultShow),y=me(e(t,`show`),_);function b(){let{value:e}=f;if(!o||!e)return;let{style:t}=e,n=o.getBoundingClientRect();t.transformOrigin=`${n.left+n.width/2}px ${n.top+n.height/2}px`}function x(e){var n,r;switch(e.key){case` `:e.preventDefault();break;case`ArrowLeft`:(n=t.onPrev)==null||n.call(t);break;case`ArrowRight`:(r=t.onNext)==null||r.call(t);break;case`ArrowUp`:e.preventDefault(),q();break;case`ArrowDown`:e.preventDefault(),ue();break;case`Escape`:de();break}}function C(e){let{onUpdateShow:n,"onUpdate:show":r}=t;n&&S(n,e),r&&S(r,e),_.value=e,m.value=!0}c(y,e=>{e?ae(`keydown`,document,x):le(`keydown`,document,x)}),r(()=>{le(`keydown`,document,x)});let w=0,T=0,E=0,O=0,k=0,A=0,j=0,N=0,P=!1;function ee(e){let{clientX:t,clientY:n}=e;E=t-w,O=n-T,pe(Y)}function te(e){let{mouseUpClientX:t,mouseUpClientY:n,mouseDownClientX:r,mouseDownClientY:i}=e,a=r-t,o=i-n;return{moveVerticalDirection:`vertical${o>0?`Top`:`Bottom`}`,moveHorizontalDirection:`horizontal${a>0?`Left`:`Right`}`,deltaHorizontal:a,deltaVertical:o}}function ne(e){let{value:t}=u;if(!t)return{offsetX:0,offsetY:0};let n=t.getBoundingClientRect(),{moveVerticalDirection:r,moveHorizontalDirection:i,deltaHorizontal:a,deltaVertical:o}=e||{},s=0,c=0;return s=n.width<=window.innerWidth?0:n.left>0?(n.width-window.innerWidth)/2:n.right<window.innerWidth?-(n.width-window.innerWidth)/2:i===`horizontalRight`?Math.min((n.width-window.innerWidth)/2,k-(a??0)):Math.max(-((n.width-window.innerWidth)/2),k-(a??0)),c=n.height<=window.innerHeight?0:n.top>0?(n.height-window.innerHeight)/2:n.bottom<window.innerHeight?-(n.height-window.innerHeight)/2:r===`verticalBottom`?Math.min((n.height-window.innerHeight)/2,A-(o??0)):Math.max(-((n.height-window.innerHeight)/2),A-(o??0)),{offsetX:s,offsetY:c}}function F(e){le(`mousemove`,document,ee),le(`mouseup`,document,F);let{clientX:t,clientY:n}=e;P=!1;let r=ne(te({mouseUpClientX:t,mouseUpClientY:n,mouseDownClientX:j,mouseDownClientY:N}));E=r.offsetX,O=r.offsetY,Y()}let I=p(zt,null);function re(e){var t,n;if((n=(t=I?.previewedImgPropsRef.value)?.onMousedown)==null||n.call(t,e),e.button!==0)return;let{clientX:r,clientY:i}=e;P=!0,w=r-E,T=i-O,k=E,A=O,j=r,N=i,Y(),ae(`mousemove`,document,ee),ae(`mouseup`,document,F)}let L=1.5,R=0,z=1,B=0;function V(e){var t,n;(n=(t=I?.previewedImgPropsRef.value)?.onDblclick)==null||n.call(t,e);let r=K();z=z===r?1:r,Y()}function H(){z=1,R=0}function ie(){var e;H(),B=0,(e=t.onPrev)==null||e.call(t)}function U(){var e;H(),B=0,(e=t.onNext)==null||e.call(t)}function oe(){B-=90,Y()}function se(){B+=90,Y()}function G(){let{value:e}=u;if(!e)return 1;let{innerWidth:t,innerHeight:n}=window,r=Math.max(1,e.naturalHeight/(n-Vt)),i=Math.max(1,e.naturalWidth/(t-Vt));return Math.max(3,r*2,i*2)}function K(){let{value:e}=u;if(!e)return 1;let{innerWidth:t,innerHeight:n}=window,r=e.naturalHeight/(n-Vt),i=e.naturalWidth/(t-Vt);return r<1&&i<1?1:Math.max(r,i)}function q(){let e=G();z<e&&(R+=1,z=Math.min(e,L**R),Y())}function ue(){if(z>.5){let e=z;--R,z=Math.max(.5,L**R);let t=e-z;Y(!1);let n=ne();z+=t,Y(!1),z-=t,E=n.offsetX,O=n.offsetY,Y()}}function J(){let e=n.value;e&&Se(e,void 0)}function Y(e=!0){let{value:t}=u;if(!t)return;let{style:n}=t,r=g(I?.previewedImgPropsRef.value?.style),i=``;if(typeof r==`string`)i=`${r};`;else for(let e in r)i+=`${vt(e)}: ${r[e]};`;let a=`transform-origin: center; transform: translateX(${E}px) translateY(${O}px) rotate(${B}deg) scale(${z});`;P?n.cssText=`${i}cursor: grabbing; transition: none;${a}`:n.cssText=`${i}cursor: grab;${a}${e?``:`transition: none;`}`,e||t.offsetHeight}function de(){if(y.value){let{onClose:e}=t;e&&S(e),C(!1),_.value=!1}}function fe(){z=K(),R=Math.ceil(Math.log(z)/Math.log(L)),E=0,O=0,Y()}let X={setThumbnailEl:e=>{o=e}};function ge(e,n){if(t.showToolbarTooltip){let{value:t}=a;return s(xe,{to:!1,theme:t.peers.Tooltip,themeOverrides:t.peerOverrides.Tooltip,keepAliveOnHover:!1},{default:()=>h.value[n],trigger:()=>e})}else return e}let _e=v(()=>{let{common:{cubicBezierEaseInOut:e},self:{toolbarIconColor:t,toolbarBorderRadius:n,toolbarBoxShadow:r,toolbarColor:i}}=a.value;return{"--n-bezier":e,"--n-toolbar-icon-color":t,"--n-toolbar-color":i,"--n-toolbar-border-radius":n,"--n-toolbar-box-shadow":r}}),{inlineThemeDisabled:ve}=W(),ye=ve?ce(`image-preview`,void 0,_e,t):void 0;function be(e){e.preventDefault()}return Object.assign({clsPrefix:i,previewRef:u,previewWrapperRef:f,previewSrc:n,mergedShow:y,appear:M(),displayed:m,previewedImgProps:I?.previewedImgPropsRef,handleWheel:be,handlePreviewMousedown:re,handlePreviewDblclick:V,syncTransformOrigin:b,handleAfterLeave:()=>{H(),B=0,m.value=!1},handleDragStart:e=>{var t,n;(n=(t=I?.previewedImgPropsRef.value)?.onDragstart)==null||n.call(t,e),e.preventDefault()},zoomIn:q,zoomOut:ue,handleDownloadClick:J,rotateCounterclockwise:oe,rotateClockwise:se,handleSwitchPrev:ie,handleSwitchNext:U,withTooltip:ge,resizeToOrignalImageSize:fe,cssVars:ve?void 0:_e,themeClass:ye?.themeClass,onRender:ye?.onRender,doUpdateShow:C,close:de},X)},render(){var e;let{clsPrefix:t,renderToolbar:n,withTooltip:r}=this,i=r(s(C,{clsPrefix:t,onClick:this.handleSwitchPrev},{default:Ft}),`tipPrevious`),a=r(s(C,{clsPrefix:t,onClick:this.handleSwitchNext},{default:It}),`tipNext`),o=r(s(C,{clsPrefix:t,onClick:this.rotateCounterclockwise},{default:()=>s(Tt,null)}),`tipCounterclockwise`),c=r(s(C,{clsPrefix:t,onClick:this.rotateClockwise},{default:()=>s(wt,null)}),`tipClockwise`),l=r(s(C,{clsPrefix:t,onClick:this.resizeToOrignalImageSize},{default:()=>s(St,null)}),`tipOriginalSize`),d=r(s(C,{clsPrefix:t,onClick:this.zoomOut},{default:()=>s(Ot,null)}),`tipZoomOut`),f=r(s(C,{clsPrefix:t,onClick:this.handleDownloadClick},{default:()=>s(xt,null)}),`tipDownload`),p=r(s(C,{clsPrefix:t,onClick:()=>this.close()},{default:Lt}),`tipClose`),g=r(s(C,{clsPrefix:t,onClick:this.zoomIn},{default:()=>s(Dt,null)}),`tipZoomIn`);return s(m,null,(e=this.$slots).default?.call(e),s(E,{show:this.mergedShow},{default:()=>{var e;return this.mergedShow||this.displayed?((e=this.onRender)==null||e.call(this),h(s(`div`,{ref:`containerRef`,class:[`${t}-image-preview-container`,this.themeClass],style:this.cssVars,onWheel:this.handleWheel},s(_,{name:`fade-in-transition`,appear:this.appear},{default:()=>this.mergedShow?s(`div`,{class:`${t}-image-preview-overlay`,onClick:()=>this.close()}):null}),this.showToolbar?s(_,{name:`fade-in-transition`,appear:this.appear},{default:()=>this.mergedShow?s(`div`,{class:`${t}-image-preview-toolbar`},n?n({nodes:{prev:i,next:a,rotateCounterclockwise:o,rotateClockwise:c,resizeToOriginalSize:l,zoomOut:d,zoomIn:g,download:f,close:p}}):s(m,null,this.onPrev?s(m,null,i,a):null,o,c,l,d,g,f,p)):null}):null,s(_,{name:`fade-in-scale-up-transition`,onAfterLeave:this.handleAfterLeave,appear:this.appear,onEnter:this.syncTransformOrigin,onBeforeLeave:this.syncTransformOrigin},{default:()=>{let{previewedImgProps:e={}}=this;return h(s(`div`,{class:`${t}-image-preview-wrapper`,ref:`previewWrapperRef`},s(`img`,Object.assign({},e,{draggable:!1,onMousedown:this.handlePreviewMousedown,onDblclick:this.handlePreviewDblclick,class:[`${t}-image-preview`,e.class],key:this.previewSrc,src:this.previewSrc,ref:`previewRef`,onDragstart:this.handleDragStart}))),[[u,this.mergedShow]])}})),[[fe,{enabled:this.mergedShow}]])):null}}))}}),Ut=j(`n-image-group`),Wt=n({name:`ImageGroup`,props:Object.assign(Object.assign({},Rt),{srcList:Array,current:Number,defaultCurrent:{type:Number,default:0},show:{type:Boolean,default:void 0},defaultShow:Boolean,onUpdateShow:[Function,Array],"onUpdate:show":[Function,Array],onUpdateCurrent:[Function,Array],"onUpdate:current":[Function,Array]}),setup(n){let{mergedClsPrefixRef:r}=W(n),i=`c${K()}`,a=l(null),o=l(n.defaultShow),s=me(e(n,`show`),o),c=l(new Map),u=v(()=>{if(n.srcList){let e=new Map;return n.srcList.forEach((t,n)=>{e.set(`p${n}`,t)}),e}return c.value}),d=v(()=>Array.from(u.value.keys())),f=()=>d.value.length;function p(e,t){n.srcList&&V(`image-group`,"`n-image` can't be placed inside `n-image-group` when image group's `src-list` prop is set.");let r=`r${e}`;return c.value.has(`r${r}`)||c.value.set(r,t),function(){c.value.has(r)||c.value.delete(r)}}let m=l(n.defaultCurrent),h=me(e(n,`current`),m),g=e=>{if(e!==h.value){let{onUpdateCurrent:t,"onUpdate:current":r}=n;t&&S(t,e),r&&S(r,e),m.value=e}},_=v(()=>d.value[h.value]),y=e=>{let t=d.value.indexOf(e);t!==h.value&&g(t)},b=v(()=>u.value.get(_.value));function x(e){let{onUpdateShow:t,"onUpdate:show":r}=n;t&&S(t,e),r&&S(r,e),o.value=e}function C(){x(!1)}let w=v(()=>{let e=(e,t)=>{for(let n=e;n<=t;n++){let e=d.value[n];if(u.value.get(e))return n}},t=e(h.value+1,f()-1);return t===void 0?e(0,h.value-1):t}),T=v(()=>{let e=(e,t)=>{for(let n=e;n>=t;n--){let e=d.value[n];if(u.value.get(e))return n}},t=e(h.value-1,0);return t===void 0?e(f()-1,h.value+1):t});function E(e){var t,r;e===1?(T.value!==void 0&&g(w.value),(t=n.onPreviewNext)==null||t.call(n)):(w.value!==void 0&&g(T.value),(r=n.onPreviewPrev)==null||r.call(n))}return t(Ut,{mergedClsPrefixRef:r,registerImageUrl:p,setThumbnailEl:e=>{var t;(t=a.value)==null||t.setThumbnailEl(e)},toggleShow:e=>{x(!0),y(e)},groupId:i,renderToolbarRef:e(n,`renderToolbar`)}),{mergedClsPrefix:r,previewInstRef:a,mergedShow:s,src:b,onClose:C,next:()=>{E(1)},prev:()=>{E(-1)}}},render(){return s(Ht,{theme:this.theme,themeOverrides:this.themeOverrides,ref:`previewInstRef`,onPrev:this.prev,onNext:this.next,src:this.src,show:this.mergedShow,showToolbar:this.showToolbar,showToolbarTooltip:this.showToolbarTooltip,renderToolbar:this.renderToolbar,onClose:this.onClose},this.$slots)}}),Gt=Object.assign({alt:String,height:[String,Number],imgProps:Object,previewedImgProps:Object,lazy:Boolean,intersectionObserverOptions:Object,objectFit:{type:String,default:`fill`},previewSrc:String,fallbackSrc:String,width:[String,Number],src:String,previewDisabled:Boolean,loadDescription:String,onError:Function,onLoad:Function},Rt),Kt=0,qt=n({name:`Image`,props:Gt,slots:Object,inheritAttrs:!1,setup(n){let o=l(null),s=l(!1),c=l(null),u=p(Ut,null),{mergedClsPrefixRef:d}=u||W(n),f=v(()=>n.previewSrc||n.src),m=l(!1),h=Kt++,g=()=>{if(n.previewDisabled||s.value)return;if(u){u.setThumbnailEl(o.value),u.toggleShow(`r${h}`);return}let{value:e}=c;e&&(e.setThumbnailEl(o.value),m.value=!0)},_={click:()=>{g()},showPreview:g},y=l(!n.lazy);a(()=>{var e;(e=o.value)==null||e.setAttribute(`data-group-id`,u?.groupId||``)}),a(()=>{if(n.lazy&&n.intersectionObserverOptions){let e,t=i(()=>{e?.(),e=void 0,e=be(o.value,n.intersectionObserverOptions,y)});r(()=>{t(),e?.()})}}),i(()=>{var e;n.src||(e=n.imgProps)==null||e.src,s.value=!1}),i(e=>{let t=(u?.registerImageUrl)?.call(u,h,f.value||``);e(()=>{t?.()})});function b(e){var t,r;_.showPreview(),(r=(t=n.imgProps)?.onClick)==null||r.call(t,e)}function x(){m.value=!1}let S=l(!1);return t(zt,{previewedImgPropsRef:e(n,`previewedImgProps`)}),Object.assign({mergedClsPrefix:d,groupId:u?.groupId,previewInstRef:c,imageRef:o,mergedPreviewSrc:f,showError:s,shouldStartLoading:y,loaded:S,mergedOnClick:e=>{b(e)},onPreviewClose:x,mergedOnError:e=>{if(!y.value)return;s.value=!0;let{onError:t,imgProps:{onError:r}={}}=n;t?.(e),r?.(e)},mergedOnLoad:e=>{let{onLoad:t,imgProps:{onLoad:r}={}}=n;t?.(e),r?.(e),S.value=!0},previewShow:m},_)},render(){var e;let{mergedClsPrefix:t,imgProps:n={},loaded:r,$attrs:i,lazy:a}=this,o=ue(this.$slots.error,()=>[]),c=(e=this.$slots).placeholder?.call(e),l=this.src||n.src,u=this.showError&&o.length?o:s(`img`,Object.assign(Object.assign({},n),{ref:`imageRef`,width:this.width||n.width,height:this.height||n.height,src:this.showError?this.fallbackSrc:a&&this.intersectionObserverOptions?this.shouldStartLoading?l:void 0:l,alt:this.alt||n.alt,"aria-label":this.alt||n.alt,onClick:this.mergedOnClick,onError:this.mergedOnError,onLoad:this.mergedOnLoad,loading:ve&&a&&!this.intersectionObserverOptions?`lazy`:`eager`,style:[n.style||``,c&&!r?{height:`0`,width:`0`,visibility:`hidden`}:``,{objectFit:this.objectFit}],"data-error":this.showError,"data-preview-src":this.previewSrc||this.src}));return s(`div`,Object.assign({},i,{role:`none`,class:[i.class,`${t}-image`,(this.previewDisabled||this.showError)&&`${t}-image--preview-disabled`]}),this.groupId?u:s(Ht,{theme:this.theme,themeOverrides:this.themeOverrides,ref:`previewInstRef`,showToolbar:this.showToolbar,showToolbarTooltip:this.showToolbarTooltip,renderToolbar:this.renderToolbar,src:this.mergedPreviewSrc,show:!this.previewDisabled&&this.previewShow,onClose:this.onPreviewClose},{default:()=>u}),!r&&c)}}),Jt={success:s(Y,null),error:s(b,null),warning:s(ee,null),info:s(k,null)},Yt=n({name:`ProgressCircle`,props:{clsPrefix:{type:String,required:!0},status:{type:String,required:!0},strokeWidth:{type:Number,required:!0},fillColor:[String,Object],railColor:String,railStyle:[String,Object],percentage:{type:Number,default:0},offsetDegree:{type:Number,default:0},showIndicator:{type:Boolean,required:!0},indicatorTextColor:String,unit:String,viewBoxWidth:{type:Number,required:!0},gapDegree:{type:Number,required:!0},gapOffsetDegree:{type:Number,default:0}},setup(e,{slots:t}){let n=v(()=>{let t=`gradient`,{fillColor:n}=e;return typeof n==`object`?`${t}-${te(JSON.stringify(n))}`:t});function r(t,r,i,a){let{gapDegree:o,viewBoxWidth:s,strokeWidth:c}=e,l=50+c/2,u=`M ${l},${l} m 0,50
      a 50,50 0 1 1 0,-100
      a 50,50 0 1 1 0,100`,d=Math.PI*2*50;return{pathString:u,pathStyle:{stroke:a===`rail`?i:typeof e.fillColor==`object`?`url(#${n.value})`:i,strokeDasharray:`${Math.min(t,100)/100*(d-o)}px ${s*8}px`,strokeDashoffset:`-${o/2}px`,transformOrigin:r?`center`:void 0,transform:r?`rotate(${r}deg)`:void 0}}}let i=()=>{let t=typeof e.fillColor==`object`,r=t?e.fillColor.stops[0]:``,i=t?e.fillColor.stops[1]:``;return t&&s(`defs`,null,s(`linearGradient`,{id:n.value,x1:`0%`,y1:`100%`,x2:`100%`,y2:`0%`},s(`stop`,{offset:`0%`,"stop-color":r}),s(`stop`,{offset:`100%`,"stop-color":i})))};return()=>{let{fillColor:n,railColor:a,strokeWidth:o,offsetDegree:c,status:l,percentage:u,showIndicator:d,indicatorTextColor:f,unit:p,gapOffsetDegree:m,clsPrefix:h}=e,{pathString:g,pathStyle:_}=r(100,0,a,`rail`),{pathString:v,pathStyle:y}=r(u,c,n,`fill`),b=100+o;return s(`div`,{class:`${h}-progress-content`,role:`none`},s(`div`,{class:`${h}-progress-graph`,"aria-hidden":!0},s(`div`,{class:`${h}-progress-graph-circle`,style:{transform:m?`rotate(${m}deg)`:void 0}},s(`svg`,{viewBox:`0 0 ${b} ${b}`},i(),s(`g`,null,s(`path`,{class:`${h}-progress-graph-circle-rail`,d:g,"stroke-width":o,"stroke-linecap":`round`,fill:`none`,style:_})),s(`g`,null,s(`path`,{class:[`${h}-progress-graph-circle-fill`,u===0&&`${h}-progress-graph-circle-fill--empty`],d:v,"stroke-width":o,"stroke-linecap":`round`,fill:`none`,style:y}))))),d?s(`div`,null,t.default?s(`div`,{class:`${h}-progress-custom-content`,role:`none`},t.default()):l==="default"?s(`div`,{class:`${h}-progress-text`,style:{color:f},role:`none`},s(`span`,{class:`${h}-progress-text__percentage`},u),s(`span`,{class:`${h}-progress-text__unit`},p)):s(`div`,{class:`${h}-progress-icon`,"aria-hidden":!0},s(C,{clsPrefix:h},{default:()=>Jt[l]}))):null)}}}),Xt={success:s(Y,null),error:s(b,null),warning:s(ee,null),info:s(k,null)},Zt=n({name:`ProgressLine`,props:{clsPrefix:{type:String,required:!0},percentage:{type:Number,default:0},railColor:String,railStyle:[String,Object],fillColor:[String,Object],status:{type:String,required:!0},indicatorPlacement:{type:String,required:!0},indicatorTextColor:String,unit:{type:String,default:`%`},processing:{type:Boolean,required:!0},showIndicator:{type:Boolean,required:!0},height:[String,Number],railBorderRadius:[String,Number],fillBorderRadius:[String,Number]},setup(e,{slots:t}){let n=v(()=>X(e.height)),r=v(()=>typeof e.fillColor==`object`?`linear-gradient(to right, ${e.fillColor?.stops[0]} , ${e.fillColor?.stops[1]})`:e.fillColor),i=v(()=>e.railBorderRadius===void 0?e.height===void 0?``:X(e.height,{c:.5}):X(e.railBorderRadius)),a=v(()=>e.fillBorderRadius===void 0?e.railBorderRadius===void 0?e.height===void 0?``:X(e.height,{c:.5}):X(e.railBorderRadius):X(e.fillBorderRadius));return()=>{let{indicatorPlacement:o,railColor:c,railStyle:l,percentage:u,unit:d,indicatorTextColor:f,status:p,showIndicator:m,processing:h,clsPrefix:g}=e;return s(`div`,{class:`${g}-progress-content`,role:`none`},s(`div`,{class:`${g}-progress-graph`,"aria-hidden":!0},s(`div`,{class:[`${g}-progress-graph-line`,{[`${g}-progress-graph-line--indicator-${o}`]:!0}]},s(`div`,{class:`${g}-progress-graph-line-rail`,style:[{backgroundColor:c,height:n.value,borderRadius:i.value},l]},s(`div`,{class:[`${g}-progress-graph-line-fill`,h&&`${g}-progress-graph-line-fill--processing`],style:{maxWidth:`${e.percentage}%`,background:r.value,height:n.value,lineHeight:n.value,borderRadius:a.value}},o===`inside`?s(`div`,{class:`${g}-progress-graph-line-indicator`,style:{color:f}},t.default?t.default():`${u}${d}`):null)))),m&&o===`outside`?s(`div`,null,t.default?s(`div`,{class:`${g}-progress-custom-content`,style:{color:f},role:`none`},t.default()):p==="default"?s(`div`,{role:`none`,class:`${g}-progress-icon ${g}-progress-icon--as-text`,style:{color:f}},u,d):s(`div`,{class:`${g}-progress-icon`,"aria-hidden":!0},s(C,{clsPrefix:g},{default:()=>Xt[p]}))):null)}}});function Qt(e,t,n=100){return`m ${n/2} ${n/2-e} a ${e} ${e} 0 1 1 0 ${2*e} a ${e} ${e} 0 1 1 0 -${2*e}`}var $t=n({name:`ProgressMultipleCircle`,props:{clsPrefix:{type:String,required:!0},viewBoxWidth:{type:Number,required:!0},percentage:{type:Array,default:[0]},strokeWidth:{type:Number,required:!0},circleGap:{type:Number,required:!0},showIndicator:{type:Boolean,required:!0},fillColor:{type:Array,default:()=>[]},railColor:{type:Array,default:()=>[]},railStyle:{type:Array,default:()=>[]}},setup(e,{slots:t}){let n=v(()=>e.percentage.map((t,n)=>`${Math.PI*t/100*(e.viewBoxWidth/2-e.strokeWidth/2*(1+2*n)-e.circleGap*n)*2}, ${e.viewBoxWidth*8}`)),r=(t,n)=>{let r=e.fillColor[n],i=typeof r==`object`?r.stops[0]:``,a=typeof r==`object`?r.stops[1]:``;return typeof e.fillColor[n]==`object`&&s(`linearGradient`,{id:`gradient-${n}`,x1:`100%`,y1:`0%`,x2:`0%`,y2:`100%`},s(`stop`,{offset:`0%`,"stop-color":i}),s(`stop`,{offset:`100%`,"stop-color":a}))};return()=>{let{viewBoxWidth:i,strokeWidth:a,circleGap:o,showIndicator:c,fillColor:l,railColor:u,railStyle:d,percentage:f,clsPrefix:p}=e;return s(`div`,{class:`${p}-progress-content`,role:`none`},s(`div`,{class:`${p}-progress-graph`,"aria-hidden":!0},s(`div`,{class:`${p}-progress-graph-circle`},s(`svg`,{viewBox:`0 0 ${i} ${i}`},s(`defs`,null,f.map((e,t)=>r(e,t))),f.map((e,t)=>s(`g`,{key:t},s(`path`,{class:`${p}-progress-graph-circle-rail`,d:Qt(i/2-a/2*(1+2*t)-o*t,a,i),"stroke-width":a,"stroke-linecap":`round`,fill:`none`,style:[{strokeDashoffset:0,stroke:u[t]},d[t]]}),s(`path`,{class:[`${p}-progress-graph-circle-fill`,e===0&&`${p}-progress-graph-circle-fill--empty`],d:Qt(i/2-a/2*(1+2*t)-o*t,a,i),"stroke-width":a,"stroke-linecap":`round`,fill:`none`,style:{strokeDasharray:n.value[t],strokeDashoffset:0,stroke:typeof l[t]==`object`?`url(#gradient-${t})`:l[t]}})))))),c&&t.default?s(`div`,null,s(`div`,{class:`${p}-progress-text`},t.default())):null)}}}),en=q([F(`progress`,{display:`inline-block`},[F(`progress-icon`,`
 color: var(--n-icon-color);
 transition: color .3s var(--n-bezier);
 `),U(`line`,`
 width: 100%;
 display: block;
 `,[F(`progress-content`,`
 display: flex;
 align-items: center;
 `,[F(`progress-graph`,{flex:1})]),F(`progress-custom-content`,{marginLeft:`14px`}),F(`progress-icon`,`
 width: 30px;
 padding-left: 14px;
 height: var(--n-icon-size-line);
 line-height: var(--n-icon-size-line);
 font-size: var(--n-icon-size-line);
 `,[U(`as-text`,`
 color: var(--n-text-color-line-outer);
 text-align: center;
 width: 40px;
 font-size: var(--n-font-size);
 padding-left: 4px;
 transition: color .3s var(--n-bezier);
 `)])]),U(`circle, dashboard`,{width:`120px`},[F(`progress-custom-content`,`
 position: absolute;
 left: 50%;
 top: 50%;
 transform: translateX(-50%) translateY(-50%);
 display: flex;
 align-items: center;
 justify-content: center;
 `),F(`progress-text`,`
 position: absolute;
 left: 50%;
 top: 50%;
 transform: translateX(-50%) translateY(-50%);
 display: flex;
 align-items: center;
 color: inherit;
 font-size: var(--n-font-size-circle);
 color: var(--n-text-color-circle);
 font-weight: var(--n-font-weight-circle);
 transition: color .3s var(--n-bezier);
 white-space: nowrap;
 `),F(`progress-icon`,`
 position: absolute;
 left: 50%;
 top: 50%;
 transform: translateX(-50%) translateY(-50%);
 display: flex;
 align-items: center;
 color: var(--n-icon-color);
 font-size: var(--n-icon-size-circle);
 `)]),U(`multiple-circle`,`
 width: 200px;
 color: inherit;
 `,[F(`progress-text`,`
 font-weight: var(--n-font-weight-circle);
 color: var(--n-text-color-circle);
 position: absolute;
 left: 50%;
 top: 50%;
 transform: translateX(-50%) translateY(-50%);
 display: flex;
 align-items: center;
 justify-content: center;
 transition: color .3s var(--n-bezier);
 `)]),F(`progress-content`,{position:`relative`}),F(`progress-graph`,{position:`relative`},[F(`progress-graph-circle`,[q(`svg`,{verticalAlign:`bottom`}),F(`progress-graph-circle-fill`,`
 stroke: var(--n-fill-color);
 transition:
 opacity .3s var(--n-bezier),
 stroke .3s var(--n-bezier),
 stroke-dasharray .3s var(--n-bezier);
 `,[U(`empty`,{opacity:0})]),F(`progress-graph-circle-rail`,`
 transition: stroke .3s var(--n-bezier);
 overflow: hidden;
 stroke: var(--n-rail-color);
 `)]),F(`progress-graph-line`,[U(`indicator-inside`,[F(`progress-graph-line-rail`,`
 height: 16px;
 line-height: 16px;
 border-radius: 10px;
 `,[F(`progress-graph-line-fill`,`
 height: inherit;
 border-radius: 10px;
 `),F(`progress-graph-line-indicator`,`
 background: #0000;
 white-space: nowrap;
 text-align: right;
 margin-left: 14px;
 margin-right: 14px;
 height: inherit;
 font-size: 12px;
 color: var(--n-text-color-line-inner);
 transition: color .3s var(--n-bezier);
 `)])]),U(`indicator-inside-label`,`
 height: 16px;
 display: flex;
 align-items: center;
 `,[F(`progress-graph-line-rail`,`
 flex: 1;
 transition: background-color .3s var(--n-bezier);
 `),F(`progress-graph-line-indicator`,`
 background: var(--n-fill-color);
 font-size: 12px;
 transform: translateZ(0);
 display: flex;
 vertical-align: middle;
 height: 16px;
 line-height: 16px;
 padding: 0 10px;
 border-radius: 10px;
 position: absolute;
 white-space: nowrap;
 color: var(--n-text-color-line-inner);
 transition:
 right .2s var(--n-bezier),
 color .3s var(--n-bezier),
 background-color .3s var(--n-bezier);
 `)]),F(`progress-graph-line-rail`,`
 position: relative;
 overflow: hidden;
 height: var(--n-rail-height);
 border-radius: 5px;
 background-color: var(--n-rail-color);
 transition: background-color .3s var(--n-bezier);
 `,[F(`progress-graph-line-fill`,`
 background: var(--n-fill-color);
 position: relative;
 border-radius: 5px;
 height: inherit;
 width: 100%;
 max-width: 0%;
 transition:
 background-color .3s var(--n-bezier),
 max-width .2s var(--n-bezier);
 `,[U(`processing`,[q(`&::after`,`
 content: "";
 background-image: var(--n-line-bg-processing);
 animation: progress-processing-animation 2s var(--n-bezier) infinite;
 `)])])])])])]),q(`@keyframes progress-processing-animation`,`
 0% {
 position: absolute;
 left: 0;
 top: 0;
 bottom: 0;
 right: 100%;
 opacity: 1;
 }
 66% {
 position: absolute;
 left: 0;
 top: 0;
 bottom: 0;
 right: 0;
 opacity: 0;
 }
 100% {
 position: absolute;
 left: 0;
 top: 0;
 bottom: 0;
 right: 0;
 opacity: 0;
 }
 `)]),tn=n({name:`Progress`,props:Object.assign(Object.assign({},D.props),{processing:Boolean,type:{type:String,default:`line`},gapDegree:Number,gapOffsetDegree:Number,status:{type:String,default:`default`},railColor:[String,Array],railStyle:[String,Array],color:[String,Array,Object],viewBoxWidth:{type:Number,default:100},strokeWidth:{type:Number,default:7},percentage:[Number,Array],unit:{type:String,default:`%`},showIndicator:{type:Boolean,default:!0},indicatorPosition:{type:String,default:`outside`},indicatorPlacement:{type:String,default:`outside`},indicatorTextColor:String,circleGap:{type:Number,default:1},height:Number,borderRadius:[String,Number],fillBorderRadius:[String,Number],offsetDegree:Number}),setup(e){let t=v(()=>e.indicatorPlacement||e.indicatorPosition),n=v(()=>{if(e.gapDegree||e.gapDegree===0)return e.gapDegree;if(e.type===`dashboard`)return 75}),{mergedClsPrefixRef:r,inlineThemeDisabled:i}=W(e),a=D(`Progress`,`-progress`,en,At,e,r),o=v(()=>{let{status:t}=e,{common:{cubicBezierEaseInOut:n},self:{fontSize:r,fontSizeCircle:i,railColor:o,railHeight:s,iconSizeCircle:c,iconSizeLine:l,textColorCircle:u,textColorLineInner:d,textColorLineOuter:f,lineBgProcessing:p,fontWeightCircle:m,[L(`iconColor`,t)]:h,[L(`fillColor`,t)]:g}}=a.value;return{"--n-bezier":n,"--n-fill-color":g,"--n-font-size":r,"--n-font-size-circle":i,"--n-font-weight-circle":m,"--n-icon-color":h,"--n-icon-size-circle":c,"--n-icon-size-line":l,"--n-line-bg-processing":p,"--n-rail-color":o,"--n-rail-height":s,"--n-text-color-circle":u,"--n-text-color-line-inner":d,"--n-text-color-line-outer":f}}),s=i?ce(`progress`,v(()=>e.status[0]),o,e):void 0;return{mergedClsPrefix:r,mergedIndicatorPlacement:t,gapDeg:n,cssVars:i?void 0:o,themeClass:s?.themeClass,onRender:s?.onRender}},render(){let{type:e,cssVars:t,indicatorTextColor:n,showIndicator:r,status:i,railColor:a,railStyle:o,color:c,percentage:l,viewBoxWidth:u,strokeWidth:d,mergedIndicatorPlacement:f,unit:p,borderRadius:m,fillBorderRadius:h,height:g,processing:_,circleGap:v,mergedClsPrefix:y,gapDeg:b,gapOffsetDegree:x,themeClass:S,$slots:C,onRender:w}=this;return w?.(),s(`div`,{class:[S,`${y}-progress`,`${y}-progress--${e}`,`${y}-progress--${i}`],style:t,"aria-valuemax":100,"aria-valuemin":0,"aria-valuenow":l,role:e===`circle`||e===`line`||e===`dashboard`?`progressbar`:`none`},e===`circle`||e===`dashboard`?s(Yt,{clsPrefix:y,status:i,showIndicator:r,indicatorTextColor:n,railColor:a,fillColor:c,railStyle:o,offsetDegree:this.offsetDegree,percentage:l,viewBoxWidth:u,strokeWidth:d,gapDegree:b===void 0?e===`dashboard`?75:0:b,gapOffsetDegree:x,unit:p},C):e===`line`?s(Zt,{clsPrefix:y,status:i,showIndicator:r,indicatorTextColor:n,railColor:a,fillColor:c,railStyle:o,percentage:l,processing:_,indicatorPlacement:f,unit:p,fillBorderRadius:h,railBorderRadius:m,height:g},C):e===`multiple-circle`?s($t,{clsPrefix:y,strokeWidth:d,railColor:a,fillColor:c,railStyle:o,viewBoxWidth:u,percentage:l,showIndicator:r,circleGap:v},C):null)}}),Q=j(`n-upload`),nn=q([F(`upload`,`width: 100%;`,[U(`dragger-inside`,[F(`upload-trigger`,`
 display: block;
 `)]),U(`drag-over`,[F(`upload-dragger`,`
 border: var(--n-dragger-border-hover);
 `)])]),F(`upload-dragger`,`
 cursor: pointer;
 box-sizing: border-box;
 width: 100%;
 text-align: center;
 border-radius: var(--n-border-radius);
 padding: 24px;
 opacity: 1;
 transition:
 opacity .3s var(--n-bezier),
 border-color .3s var(--n-bezier),
 background-color .3s var(--n-bezier);
 background-color: var(--n-dragger-color);
 border: var(--n-dragger-border);
 `,[q(`&:hover`,`
 border: var(--n-dragger-border-hover);
 `),U(`disabled`,`
 cursor: not-allowed;
 `)]),F(`upload-trigger`,`
 display: inline-block;
 box-sizing: border-box;
 opacity: 1;
 transition: opacity .3s var(--n-bezier);
 `,[q(`+`,[F(`upload-file-list`,`margin-top: 8px;`)]),U(`disabled`,`
 opacity: var(--n-item-disabled-opacity);
 cursor: not-allowed;
 `),U(`image-card`,`
 width: 96px;
 height: 96px;
 `,[F(`base-icon`,`
 font-size: 24px;
 `),F(`upload-dragger`,`
 padding: 0;
 height: 100%;
 width: 100%;
 display: flex;
 align-items: center;
 justify-content: center;
 `)])]),F(`upload-file-list`,`
 line-height: var(--n-line-height);
 opacity: 1;
 transition: opacity .3s var(--n-bezier);
 `,[q(`a, img`,`outline: none;`),U(`disabled`,`
 opacity: var(--n-item-disabled-opacity);
 cursor: not-allowed;
 `,[F(`upload-file`,`cursor: not-allowed;`)]),U(`grid`,`
 display: grid;
 grid-template-columns: repeat(auto-fill, 96px);
 grid-gap: 8px;
 margin-top: 0;
 `),F(`upload-file`,`
 display: block;
 box-sizing: border-box;
 cursor: default;
 padding: 0px 12px 0 6px;
 transition: background-color .3s var(--n-bezier);
 border-radius: var(--n-border-radius);
 `,[ne(),F(`progress`,[ne({foldPadding:!0})]),q(`&:hover`,`
 background-color: var(--n-item-color-hover);
 `,[F(`upload-file-info`,[G(`action`,`
 opacity: 1;
 `)])]),U(`image-type`,`
 border-radius: var(--n-border-radius);
 text-decoration: underline;
 text-decoration-color: #0000;
 `,[F(`upload-file-info`,`
 padding-top: 0px;
 padding-bottom: 0px;
 width: 100%;
 height: 100%;
 display: flex;
 justify-content: space-between;
 align-items: center;
 padding: 6px 0;
 `,[F(`progress`,`
 padding: 2px 0;
 margin-bottom: 0;
 `),G(`name`,`
 padding: 0 8px;
 `),G(`thumbnail`,`
 width: 32px;
 height: 32px;
 font-size: 28px;
 display: flex;
 justify-content: center;
 align-items: center;
 `,[q(`img`,`
 width: 100%;
 `)])])]),U(`text-type`,[F(`progress`,`
 box-sizing: border-box;
 padding-bottom: 6px;
 margin-bottom: 6px;
 `)]),U(`image-card-type`,`
 position: relative;
 width: 96px;
 height: 96px;
 border: var(--n-item-border-image-card);
 border-radius: var(--n-border-radius);
 padding: 0;
 display: flex;
 align-items: center;
 justify-content: center;
 transition: border-color .3s var(--n-bezier), background-color .3s var(--n-bezier);
 border-radius: var(--n-border-radius);
 overflow: hidden;
 `,[F(`progress`,`
 position: absolute;
 left: 8px;
 bottom: 8px;
 right: 8px;
 width: unset;
 `),F(`upload-file-info`,`
 padding: 0;
 width: 100%;
 height: 100%;
 `,[G(`thumbnail`,`
 width: 100%;
 height: 100%;
 display: flex;
 flex-direction: column;
 align-items: center;
 justify-content: center;
 font-size: 36px;
 `,[q(`img`,`
 width: 100%;
 `)])]),q(`&::before`,`
 position: absolute;
 z-index: 1;
 left: 0;
 right: 0;
 top: 0;
 bottom: 0;
 border-radius: inherit;
 opacity: 0;
 transition: opacity .2s var(--n-bezier);
 content: "";
 `),q(`&:hover`,[q(`&::before`,`opacity: 1;`),F(`upload-file-info`,[G(`thumbnail`,`opacity: .12;`)])])]),U(`error-status`,[q(`&:hover`,`
 background-color: var(--n-item-color-hover-error);
 `),F(`upload-file-info`,[G(`name`,`color: var(--n-item-text-color-error);`),G(`thumbnail`,`color: var(--n-item-text-color-error);`)]),U(`image-card-type`,`
 border: var(--n-item-border-image-card-error);
 `)]),U(`with-url`,`
 cursor: pointer;
 `,[F(`upload-file-info`,[G(`name`,`
 color: var(--n-item-text-color-success);
 text-decoration-color: var(--n-item-text-color-success);
 `,[q(`a`,`
 text-decoration: underline;
 `)])])]),F(`upload-file-info`,`
 position: relative;
 padding-top: 6px;
 padding-bottom: 6px;
 display: flex;
 flex-wrap: nowrap;
 `,[G(`thumbnail`,`
 font-size: 18px;
 opacity: 1;
 transition: opacity .2s var(--n-bezier);
 color: var(--n-item-icon-color);
 `,[F(`base-icon`,`
 margin-right: 2px;
 vertical-align: middle;
 transition: color .3s var(--n-bezier);
 `)]),G(`action`,`
 padding-top: inherit;
 padding-bottom: inherit;
 position: absolute;
 right: 0;
 top: 0;
 bottom: 0;
 width: 80px;
 display: flex;
 align-items: center;
 transition: opacity .2s var(--n-bezier);
 justify-content: flex-end;
 opacity: 0;
 `,[F(`button`,[q(`&:not(:last-child)`,{marginRight:`4px`}),F(`base-icon`,[q(`svg`,[de()])])]),U(`image-type`,`
 position: relative;
 max-width: 80px;
 width: auto;
 `),U(`image-card-type`,`
 z-index: 2;
 position: absolute;
 width: 100%;
 height: 100%;
 left: 0;
 right: 0;
 bottom: 0;
 top: 0;
 display: flex;
 justify-content: center;
 align-items: center;
 `)]),G(`name`,`
 color: var(--n-item-text-color);
 flex: 1;
 display: flex;
 justify-content: center;
 text-overflow: ellipsis;
 overflow: hidden;
 flex-direction: column;
 text-decoration-color: #0000;
 font-size: var(--n-font-size);
 transition:
 color .3s var(--n-bezier),
 text-decoration-color .3s var(--n-bezier); 
 `,[q(`a`,`
 color: inherit;
 text-decoration: underline;
 `)])])])]),F(`upload-file-input`,`
 display: none;
 width: 0;
 height: 0;
 opacity: 0;
 `)]),rn=n({name:`UploadDragger`,__UPLOAD_DRAGGER__:!0,setup(e,{slots:t}){let n=p(Q,null);return n||V(`upload-dragger`,"`n-upload-dragger` must be placed inside `n-upload`."),()=>{let{mergedClsPrefixRef:{value:e},mergedDisabledRef:{value:r},maxReachedRef:{value:i}}=n;return s(`div`,{class:[`${e}-upload-dragger`,(r||i)&&`${e}-upload-dragger--disabled`]},t)}}});function an(){return s(`svg`,{xmlns:`http://www.w3.org/2000/svg`,viewBox:`0 0 28 28`},s(`g`,{fill:`none`},s(`path`,{d:`M21.75 3A3.25 3.25 0 0 1 25 6.25v15.5A3.25 3.25 0 0 1 21.75 25H6.25A3.25 3.25 0 0 1 3 21.75V6.25A3.25 3.25 0 0 1 6.25 3h15.5zm.583 20.4l-7.807-7.68a.75.75 0 0 0-.968-.07l-.084.07l-7.808 7.68c.183.065.38.1.584.1h15.5c.204 0 .4-.035.583-.1l-7.807-7.68l7.807 7.68zM21.75 4.5H6.25A1.75 1.75 0 0 0 4.5 6.25v15.5c0 .208.036.408.103.593l7.82-7.692a2.25 2.25 0 0 1 3.026-.117l.129.117l7.82 7.692c.066-.185.102-.385.102-.593V6.25a1.75 1.75 0 0 0-1.75-1.75zm-3.25 3a2.5 2.5 0 1 1 0 5a2.5 2.5 0 0 1 0-5zm0 1.5a1 1 0 1 0 0 2a1 1 0 0 0 0-2z`,fill:`currentColor`})))}function on(){return s(`svg`,{xmlns:`http://www.w3.org/2000/svg`,viewBox:`0 0 28 28`},s(`g`,{fill:`none`},s(`path`,{d:`M6.4 2A2.4 2.4 0 0 0 4 4.4v19.2A2.4 2.4 0 0 0 6.4 26h15.2a2.4 2.4 0 0 0 2.4-2.4V11.578c0-.729-.29-1.428-.805-1.944l-6.931-6.931A2.4 2.4 0 0 0 14.567 2H6.4zm-.9 2.4a.9.9 0 0 1 .9-.9H14V10a2 2 0 0 0 2 2h6.5v11.6a.9.9 0 0 1-.9.9H6.4a.9.9 0 0 1-.9-.9V4.4zm16.44 6.1H16a.5.5 0 0 1-.5-.5V4.06l6.44 6.44z`,fill:`currentColor`})))}var sn=n({name:`UploadProgress`,props:{show:Boolean,percentage:{type:Number,required:!0},status:{type:String,required:!0}},setup(){return{mergedTheme:p(Q).mergedThemeRef}},render(){return s(N,null,{default:()=>this.show?s(tn,{type:`line`,showIndicator:!1,percentage:this.percentage,status:this.status,height:2,theme:this.mergedTheme.peers.Progress,themeOverrides:this.mergedTheme.peerOverrides.Progress}):null})}}),cn=function(e,t,n,r){function i(e){return e instanceof n?e:new n(function(t){t(e)})}return new(n||=Promise)(function(n,a){function o(e){try{c(r.next(e))}catch(e){a(e)}}function s(e){try{c(r.throw(e))}catch(e){a(e)}}function c(e){e.done?n(e.value):i(e.value).then(o,s)}c((r=r.apply(e,t||[])).next())})};function ln(e){return e.includes(`image/`)}function un(e=``){let t=e.split(`/`),n=t[t.length-1].split(/#|\?/)[0];return(/\.[^./\\]*$/.exec(n)||[``])[0]}var dn=/(webp|svg|png|gif|jpg|jpeg|jfif|bmp|dpg|ico)$/i,fn=e=>{if(e.type)return ln(e.type);let t=un(e.name||``);if(dn.test(t))return!0;let n=e.thumbnailUrl||e.url||``,r=un(n);return!!(/^data:image\//.test(n)||dn.test(r))};function pn(e){return cn(this,void 0,void 0,function*(){return yield new Promise(t=>{if(!e.type||!ln(e.type)){t(``);return}t(window.URL.createObjectURL(e))})})}var mn=T&&window.FileReader&&window.File;function hn(e){return e.isDirectory}function gn(e){return e.isFile}function _n(e,t){return cn(this,void 0,void 0,function*(){let n=[];function r(e){return cn(this,void 0,void 0,function*(){for(let i of e)if(i){if(t&&hn(i)){let e=i.createReader(),t=[],n;try{do n=yield new Promise((t,n)=>{e.readEntries(t,n)}),t=t.concat(n);while(n.length>0)}catch(e){O(`upload`,`error happens when handling directory upload`,e)}yield r(t)}else if(gn(i))try{let e=yield new Promise((e,t)=>{i.file(e,t)});n.push({file:e,entry:i,source:`dnd`})}catch(e){O(`upload`,`error happens when handling file upload`,e)}}})}return yield r(e),n})}function $(e){let{id:t,name:n,percentage:r,status:i,url:a,file:o,thumbnailUrl:s,type:c,fullPath:l,batchId:u}=e;return{id:t,name:n,percentage:r??null,status:i,url:a??null,file:o??null,thumbnailUrl:s??null,type:c??null,fullPath:l??null,batchId:u??null}}function vn(e,t,n){return e=e.toLowerCase(),t=t.toLocaleLowerCase(),n=n.toLocaleLowerCase(),n.split(`,`).map(e=>e.trim()).filter(Boolean).some(n=>{if(n.startsWith(`.`)){if(e.endsWith(n))return!0}else if(n.includes(`/`)){let[e,r]=t.split(`/`),[i,a]=n.split(`/`);if((i===`*`||e&&i&&i===e)&&(a===`*`||r&&a&&a===r))return!0}else return!0;return!1})}var yn=function(e,t,n,r){function i(e){return e instanceof n?e:new n(function(t){t(e)})}return new(n||=Promise)(function(n,a){function o(e){try{c(r.next(e))}catch(e){a(e)}}function s(e){try{c(r.throw(e))}catch(e){a(e)}}function c(e){e.done?n(e.value):i(e.value).then(o,s)}c((r=r.apply(e,t||[])).next())})},bn={paddingMedium:`0 3px`,heightMedium:`24px`,iconSizeMedium:`18px`},xn=n({name:`UploadFile`,props:{clsPrefix:{type:String,required:!0},file:{type:Object,required:!0},listType:{type:String,required:!0},index:{type:Number,required:!0}},setup(e){let t=p(Q),n=l(null),r=l(``),a=v(()=>{let{file:t}=e;return t.status===`finished`?`success`:t.status===`error`?`error`:`info`}),o=v(()=>{let{file:t}=e;if(t.status===`error`)return`error`}),s=v(()=>{let{file:t}=e;return t.status===`uploading`}),c=v(()=>{if(!t.showCancelButtonRef.value)return!1;let{file:n}=e;return[`uploading`,`pending`,`error`].includes(n.status)}),u=v(()=>{if(!t.showRemoveButtonRef.value)return!1;let{file:n}=e;return[`finished`].includes(n.status)}),d=v(()=>{if(!t.showDownloadButtonRef.value)return!1;let{file:n}=e;return[`finished`].includes(n.status)}),f=v(()=>{if(!t.showRetryButtonRef.value)return!1;let{file:n}=e;return[`error`].includes(n.status)}),m=I(()=>r.value||e.file.thumbnailUrl||e.file.url),h=v(()=>{if(!t.showPreviewButtonRef.value)return!1;let{file:{status:n},listType:r}=e;return[`finished`].includes(n)&&m.value&&r===`image-card`});function g(){return yn(this,void 0,void 0,function*(){let n=t.onRetryRef.value;n&&(yield n({file:e.file}))===!1||t.submit({fileId:e.file.id})})}function _(t){t.preventDefault();let{file:n}=e;[`finished`,`pending`,`error`].includes(n.status)?x(n):[`uploading`].includes(n.status)?C(n):y(`upload`,`The button clicked type is unknown.`)}function b(t){t.preventDefault(),S(e.file)}function x(n){let{xhrMap:r,doChange:i,onRemoveRef:{value:a},mergedFileListRef:{value:o}}=t;Promise.resolve(a?a({file:Object.assign({},n),fileList:o,index:e.index}):!0).then(e=>{if(e===!1)return;let t=Object.assign({},n,{status:`removed`});r.delete(n.id),i(t,void 0,{remove:!0})})}function S(e){let{onDownloadRef:{value:n},customDownloadRef:{value:r}}=t;Promise.resolve(n?n(Object.assign({},e)):!0).then(t=>{t!==!1&&(r?r(Object.assign({},e)):Se(e.url,e.name))})}function C(e){let{xhrMap:n}=t;n.get(e.id)?.abort(),x(Object.assign({},e))}function w(r){let{onPreviewRef:{value:i}}=t;if(i)i(e.file,{event:r});else if(e.listType===`image-card`){let{value:e}=n;if(!e)return;e.showPreview()}}let T=()=>yn(this,void 0,void 0,function*(){let{listType:n}=e;n!==`image`&&n!==`image-card`||t.shouldUseThumbnailUrlRef.value(e.file)&&(r.value=yield t.getFileThumbnailUrlResolver(e.file))});return i(()=>{T()}),{mergedTheme:t.mergedThemeRef,progressStatus:a,buttonType:o,showProgress:s,disabled:t.mergedDisabledRef,showCancelButton:c,showRemoveButton:u,showDownloadButton:d,showRetryButton:f,showPreviewButton:h,mergedThumbnailUrl:m,shouldUseThumbnailUrl:t.shouldUseThumbnailUrlRef,renderIcon:t.renderIconRef,imageRef:n,handleRemoveOrCancelClick:_,handleDownloadClick:b,handleRetryClick:g,handlePreviewClick:w}},render(){let{clsPrefix:e,mergedTheme:t,listType:n,file:r,renderIcon:i}=this,a,o=n===`image`;a=o||n===`image-card`?!this.shouldUseThumbnailUrl(r)||!this.mergedThumbnailUrl?s(`span`,{class:`${e}-upload-file-info__thumbnail`},i?i(r):fn(r)?s(C,{clsPrefix:e},{default:an}):s(C,{clsPrefix:e},{default:on})):s(`a`,{rel:`noopener noreferer`,target:`_blank`,href:r.url||void 0,class:`${e}-upload-file-info__thumbnail`,onClick:this.handlePreviewClick},n===`image-card`?s(qt,{src:this.mergedThumbnailUrl||void 0,previewSrc:r.url||void 0,alt:r.name,ref:`imageRef`}):s(`img`,{src:this.mergedThumbnailUrl||void 0,alt:r.name})):s(`span`,{class:`${e}-upload-file-info__thumbnail`},i?i(r):s(C,{clsPrefix:e},{default:()=>s(yt,null)}));let c=s(sn,{show:this.showProgress,percentage:r.percentage||0,status:this.progressStatus}),l=n===`text`||n===`image`;return s(`div`,{class:[`${e}-upload-file`,`${e}-upload-file--${this.progressStatus}-status`,r.url&&r.status!==`error`&&n!==`image-card`&&`${e}-upload-file--with-url`,`${e}-upload-file--${n}-type`]},s(`div`,{class:`${e}-upload-file-info`},a,s(`div`,{class:`${e}-upload-file-info__name`},l&&(r.url&&r.status!==`error`?s(`a`,{rel:`noopener noreferer`,target:`_blank`,href:r.url||void 0,onClick:this.handlePreviewClick},r.name):s(`span`,{onClick:this.handlePreviewClick},r.name)),o&&c),s(`div`,{class:[`${e}-upload-file-info__action`,`${e}-upload-file-info__action--${n}-type`]},this.showPreviewButton?s(P,{key:`preview`,quaternary:!0,type:this.buttonType,onClick:this.handlePreviewClick,theme:t.peers.Button,themeOverrides:t.peerOverrides.Button,builtinThemeOverrides:bn},{icon:()=>s(C,{clsPrefix:e},{default:()=>s(ge,null)})}):null,(this.showRemoveButton||this.showCancelButton)&&!this.disabled&&s(P,{key:`cancelOrTrash`,theme:t.peers.Button,themeOverrides:t.peerOverrides.Button,quaternary:!0,builtinThemeOverrides:bn,type:this.buttonType,onClick:this.handleRemoveOrCancelClick},{icon:()=>s(A,null,{default:()=>this.showRemoveButton?s(C,{clsPrefix:e,key:`trash`},{default:()=>s(Et,null)}):s(C,{clsPrefix:e,key:`cancel`},{default:()=>s(bt,null)})})}),this.showRetryButton&&!this.disabled&&s(P,{key:`retry`,quaternary:!0,type:this.buttonType,onClick:this.handleRetryClick,theme:t.peers.Button,themeOverrides:t.peerOverrides.Button,builtinThemeOverrides:bn},{icon:()=>s(C,{clsPrefix:e},{default:()=>s(Ct,null)})}),this.showDownloadButton?s(P,{key:`download`,quaternary:!0,type:this.buttonType,onClick:this.handleDownloadClick,theme:t.peers.Button,themeOverrides:t.peerOverrides.Button,builtinThemeOverrides:bn},{icon:()=>s(C,{clsPrefix:e},{default:()=>s(xt,null)})}):null)),!o&&c)}}),Sn=n({name:`UploadTrigger`,props:{abstract:Boolean},slots:Object,setup(e,{slots:t}){let n=p(Q,null);n||V(`upload-trigger`,"`n-upload-trigger` must be placed inside `n-upload`.");let{mergedClsPrefixRef:r,mergedDisabledRef:i,maxReachedRef:a,listTypeRef:o,dragOverRef:c,openOpenFileDialog:l,draggerInsideRef:u,handleFileAddition:d,mergedDirectoryDndRef:f,triggerClassRef:m,triggerStyleRef:h}=n,g=v(()=>o.value===`image-card`);function _(){i.value||a.value||l()}function y(e){e.preventDefault(),c.value=!0}function b(e){e.preventDefault(),c.value=!0}function x(e){e.preventDefault(),c.value=!1}function S(e){if(e.preventDefault(),!u.value||i.value||a.value){c.value=!1;return}let t=e.dataTransfer?.items;t?.length?_n(Array.from(t).map(e=>e.webkitGetAsEntry()),f.value).then(e=>{d(e)}).finally(()=>{c.value=!1}):c.value=!1}return()=>{let{value:n}=r;return e.abstract?t.default?.call(t,{handleClick:_,handleDrop:S,handleDragOver:y,handleDragEnter:b,handleDragLeave:x}):s(`div`,{class:[`${n}-upload-trigger`,(i.value||a.value)&&`${n}-upload-trigger--disabled`,g.value&&`${n}-upload-trigger--image-card`,m.value],style:h.value,onClick:_,onDrop:S,onDragover:y,onDragenter:b,onDragleave:x},g.value?s(rn,null,{default:()=>ue(t.default,()=>[s(C,{clsPrefix:n},{default:()=>s(_e,null)})])}):t)}}}),Cn=n({name:`UploadFileList`,setup(e,{slots:t}){let n=p(Q,null);n||V(`upload-file-list`,"`n-upload-file-list` must be placed inside `n-upload`.");let{abstractRef:r,mergedClsPrefixRef:i,listTypeRef:a,mergedFileListRef:o,fileListClassRef:c,fileListStyleRef:l,cssVarsRef:u,themeClassRef:d,maxReachedRef:f,showTriggerRef:m,imageGroupPropsRef:h}=n,g=v(()=>a.value===`image-card`),_=()=>o.value.map((e,t)=>s(xn,{clsPrefix:i.value,key:e.id,file:e,index:t,listType:a.value})),y=()=>g.value?s(Wt,Object.assign({},h.value),{default:_}):s(N,{group:!0},{default:_});return()=>{let{value:e}=i,{value:n}=r;return s(`div`,{class:[`${e}-upload-file-list`,g.value&&`${e}-upload-file-list--grid`,n?d?.value:void 0,c.value],style:[n&&u?u.value:``,l.value]},y(),m.value&&!f.value&&g.value&&s(Sn,null,t))}}}),wn=function(e,t,n,r){function i(e){return e instanceof n?e:new n(function(t){t(e)})}return new(n||=Promise)(function(n,a){function o(e){try{c(r.next(e))}catch(e){a(e)}}function s(e){try{c(r.throw(e))}catch(e){a(e)}}function c(e){e.done?n(e.value):i(e.value).then(o,s)}c((r=r.apply(e,t||[])).next())})};function Tn(e,t,n){let{doChange:r,xhrMap:i}=e,a=0;function o(n){let o=Object.assign({},t,{status:`error`,percentage:a});i.delete(t.id),o=$(e.onError?.call(e,{file:o,event:n})||o),r(o,n)}function s(s){if(e.isErrorState){if(e.isErrorState(n)){o(s);return}}else if(n.status<200||n.status>=300){o(s);return}let c=Object.assign({},t,{status:`finished`,percentage:a});i.delete(t.id),c=$(e.onFinish?.call(e,{file:c,event:s})||c),r(c,s)}return{handleXHRLoad:s,handleXHRError:o,handleXHRAbort(e){let n=Object.assign({},t,{status:`removed`,file:null,percentage:a});i.delete(t.id),r(n,e)},handleXHRProgress(e){let n=Object.assign({},t,{status:`uploading`});if(e.lengthComputable){let t=Math.ceil(e.loaded/e.total*100);n.percentage=t,a=t}r(n,e)}}}function En(e){let{inst:t,file:n,data:r,headers:i,withCredentials:a,action:o,customRequest:s}=e,{doChange:c}=e.inst,l=0;s({file:n,data:r,headers:i,withCredentials:a,action:o,onProgress(e){let t=Object.assign({},n,{status:`uploading`}),r=e.percent;t.percentage=r,l=r,c(t)},onFinish(){let e=Object.assign({},n,{status:`finished`,percentage:l});e=$(t.onFinish?.call(t,{file:e})||e),c(e)},onError(){let e=Object.assign({},n,{status:`error`,percentage:l});e=$(t.onError?.call(t,{file:e})||e),c(e)}})}function Dn(e,t,n){let r=Tn(e,t,n);n.onabort=r.handleXHRAbort,n.onerror=r.handleXHRError,n.onload=r.handleXHRLoad,n.upload&&(n.upload.onprogress=r.handleXHRProgress)}function On(e,t){return typeof e==`function`?e({file:t}):e||{}}function kn(e,t,n){let r=On(t,n);r&&Object.keys(r).forEach(t=>{e.setRequestHeader(t,r[t])})}function An(e,t,n){let r=On(t,n);r&&Object.keys(r).forEach(t=>{e.append(t,r[t])})}function jn(e,t,n,{method:r,action:i,withCredentials:a,responseType:o,headers:s,data:c}){let l=new XMLHttpRequest;l.responseType=o,e.xhrMap.set(n.id,l),l.withCredentials=a;let u=new FormData;if(An(u,c,n),n.file!==null&&u.append(t,n.file),Dn(e,n,l),i!==void 0){l.open(r.toUpperCase(),i),kn(l,s,n),l.send(u);let t=Object.assign({},n,{status:`uploading`});e.doChange(t)}}var Mn=n({name:`Upload`,props:Object.assign(Object.assign({},D.props),{name:{type:String,default:`file`},accept:String,action:String,customRequest:Function,directory:Boolean,directoryDnd:{type:Boolean,default:void 0},method:{type:String,default:`POST`},multiple:Boolean,showFileList:{type:Boolean,default:!0},data:[Object,Function],headers:[Object,Function],withCredentials:Boolean,responseType:{type:String,default:``},disabled:{type:Boolean,default:void 0},onChange:Function,onRemove:Function,onFinish:Function,onError:Function,onRetry:Function,onBeforeUpload:Function,isErrorState:Function,onDownload:Function,customDownload:Function,defaultUpload:{type:Boolean,default:!0},fileList:Array,"onUpdate:fileList":[Function,Array],onUpdateFileList:[Function,Array],fileListClass:String,fileListStyle:[String,Object],defaultFileList:{type:Array,default:()=>[]},showCancelButton:{type:Boolean,default:!0},showRemoveButton:{type:Boolean,default:!0},showDownloadButton:Boolean,showRetryButton:{type:Boolean,default:!0},showPreviewButton:{type:Boolean,default:!0},listType:{type:String,default:`text`},onPreview:Function,shouldUseThumbnailUrl:{type:Function,default:e=>mn?fn(e):!1},createThumbnailUrl:Function,abstract:Boolean,max:Number,showTrigger:{type:Boolean,default:!0},imageGroupProps:Object,inputProps:Object,triggerClass:String,triggerStyle:[String,Object],renderIcon:Function}),setup(n){n.abstract&&n.listType===`image-card`&&V(`upload`,`when the list-type is image-card, abstract is not supported.`);let{mergedClsPrefixRef:r,inlineThemeDisabled:i,mergedRtlRef:a}=W(n),s=D(`Upload`,`-upload`,nn,Mt,n,r),c=B(`Upload`,a,r),u=re(n),d=l(n.defaultFileList),f=e(n,`fileList`),p=l(null),m={value:!1},h=l(!1),g=new Map,_=me(f,d),y=v(()=>_.value.map($)),b=v(()=>{let{max:e}=n;return e===void 0?!1:y.value.length>=e});function x(){var e;(e=p.value)==null||e.click()}function C(e){let t=e.target;O(t.files?Array.from(t.files).map(e=>({file:e,entry:null,source:`input`})):null,e),t.value=``}function w(e){let{"onUpdate:fileList":t,onUpdateFileList:r}=n;t&&S(t,e),r&&S(r,e),d.value=e}let T=v(()=>n.multiple||n.directory),E=(e,t,r={append:!1,remove:!1})=>{let{append:i,remove:a}=r,o=Array.from(y.value),s=o.findIndex(t=>t.id===e.id);if(i||a||~s){i?o.push(e):a?o.splice(s,1):o.splice(s,1,e);let{onChange:r}=n;r&&r({file:e,fileList:o,event:t}),w(o)}};function O(e,t){if(!e||e.length===0)return;let{onBeforeUpload:r}=n;e=T.value?e:[e[0]];let{max:i,accept:a}=n;e=e.filter(({file:e,source:t})=>t===`dnd`&&a?.trim()?vn(e.name,e.type,a):!0),i&&(e=e.slice(0,i-y.value.length));let s=K();Promise.all(e.map(e=>wn(this,[e],void 0,function*({file:e,entry:t}){let n={id:K(),batchId:s,name:e.name,status:`pending`,percentage:0,file:e,url:null,type:e.type,thumbnailUrl:null,fullPath:t?.fullPath??`/${e.webkitRelativePath||e.name}`};return!r||(yield r({file:n,fileList:y.value}))!==!1?n:null}))).then(e=>wn(this,void 0,void 0,function*(){let n=Promise.resolve();e.forEach(e=>{n=n.then(o).then(()=>{e&&E(e,t,{append:!0})})}),yield n})).then(()=>{n.defaultUpload&&k()})}function k({fileId:e,retry:t=!1}={}){let{method:r,action:i,withCredentials:a,headers:o,data:s,name:c}=n,l=e===void 0?y.value:y.value.filter(t=>t.id===e),u=t||e!==void 0;l.forEach(e=>{let{status:t}=e;(t===`pending`||t===`error`&&u)&&(n.customRequest?En({inst:{doChange:E,xhrMap:g,onFinish:n.onFinish,onError:n.onError},file:e,action:i,withCredentials:a,headers:o,data:s,customRequest:n.customRequest}):jn({doChange:E,xhrMap:g,onFinish:n.onFinish,onError:n.onError,isErrorState:n.isErrorState},c,e,{method:r,action:i,withCredentials:a,responseType:n.responseType,headers:o,data:s}))})}function A(e){if(e.thumbnailUrl)return e.thumbnailUrl;let{createThumbnailUrl:t}=n;return t?t(e.file,e)??(e.url||``):e.url?e.url:e.file?pn(e.file):``}let j=v(()=>{let{common:{cubicBezierEaseInOut:e},self:{draggerColor:t,draggerBorder:n,draggerBorderHover:r,itemColorHover:i,itemColorHoverError:a,itemTextColorError:o,itemTextColorSuccess:c,itemTextColor:l,itemIconColor:u,itemDisabledOpacity:d,lineHeight:f,borderRadius:p,fontSize:m,itemBorderImageCardError:h,itemBorderImageCard:g}}=s.value;return{"--n-bezier":e,"--n-border-radius":p,"--n-dragger-border":n,"--n-dragger-border-hover":r,"--n-dragger-color":t,"--n-font-size":m,"--n-item-color-hover":i,"--n-item-color-hover-error":a,"--n-item-disabled-opacity":d,"--n-item-icon-color":u,"--n-item-text-color":l,"--n-item-text-color-error":o,"--n-item-text-color-success":c,"--n-line-height":f,"--n-item-border-image-card-error":h,"--n-item-border-image-card":g}}),M=i?ce(`upload`,void 0,j,n):void 0;t(Q,{mergedClsPrefixRef:r,mergedThemeRef:s,showCancelButtonRef:e(n,`showCancelButton`),showDownloadButtonRef:e(n,`showDownloadButton`),showRemoveButtonRef:e(n,`showRemoveButton`),showRetryButtonRef:e(n,`showRetryButton`),onRemoveRef:e(n,`onRemove`),onDownloadRef:e(n,`onDownload`),customDownloadRef:e(n,`customDownload`),mergedFileListRef:y,triggerClassRef:e(n,`triggerClass`),triggerStyleRef:e(n,`triggerStyle`),shouldUseThumbnailUrlRef:e(n,`shouldUseThumbnailUrl`),renderIconRef:e(n,`renderIcon`),xhrMap:g,submit:k,doChange:E,showPreviewButtonRef:e(n,`showPreviewButton`),onPreviewRef:e(n,`onPreview`),getFileThumbnailUrlResolver:A,listTypeRef:e(n,`listType`),dragOverRef:h,openOpenFileDialog:x,draggerInsideRef:m,handleFileAddition:O,mergedDisabledRef:u.mergedDisabledRef,maxReachedRef:b,fileListClassRef:e(n,`fileListClass`),fileListStyleRef:e(n,`fileListStyle`),abstractRef:e(n,`abstract`),acceptRef:e(n,`accept`),cssVarsRef:i?void 0:j,themeClassRef:M?.themeClass,onRender:M?.onRender,showTriggerRef:e(n,`showTrigger`),imageGroupPropsRef:e(n,`imageGroupProps`),mergedDirectoryDndRef:v(()=>n.directoryDnd??n.directory),onRetryRef:e(n,`onRetry`)});let N={clear:()=>{d.value=[]},submit:k,openOpenFileDialog:x};return Object.assign({mergedClsPrefix:r,draggerInsideRef:m,rtlEnabled:c,inputElRef:p,mergedTheme:s,dragOver:h,mergedMultiple:T,cssVars:i?void 0:j,themeClass:M?.themeClass,onRender:M?.onRender,handleFileInputChange:C},N)},render(){let{draggerInsideRef:e,mergedClsPrefix:t,$slots:n,directory:r,onRender:i}=this;n.default&&!this.abstract&&n.default()[0]?.type?.__UPLOAD_DRAGGER__&&(e.value=!0);let a=s(`input`,Object.assign({},this.inputProps,{ref:`inputElRef`,type:`file`,class:`${t}-upload-file-input`,accept:this.accept,multiple:this.mergedMultiple,onChange:this.handleFileInputChange,webkitdirectory:r||void 0,directory:r||void 0}));return this.abstract?s(m,null,n.default?.call(n),s(f,{to:`body`},a)):(i?.(),s(`div`,{class:[`${t}-upload`,this.rtlEnabled&&`${t}-upload--rtl`,e.value&&`${t}-upload--dragger-inside`,this.dragOver&&`${t}-upload--drag-over`,this.themeClass],style:this.cssVars},a,this.showTrigger&&this.listType!==`image-card`&&s(Sn,null,n),this.showFileList&&s(Cn,null,n)))}}),Nn=`yy_ref_frames`,Pn=1800*1e3;function Fn(e,t=``){let n=Array.isArray(e)?e.filter(Boolean):[];if(!(!n.length&&!t))try{sessionStorage.setItem(Nn,JSON.stringify({urls:n,videoUrl:t,ts:Date.now()}))}catch{}}function In(){let e={frames:[],videoUrl:``};try{let t=sessionStorage.getItem(Nn);if(!t)return e;let{urls:n,videoUrl:r,ts:i}=JSON.parse(t);return Date.now()-i>=Pn?e:{frames:Array.isArray(n)?n.filter(Boolean):[],videoUrl:r||``}}catch{return e}}function Ln(){try{sessionStorage.removeItem(Nn)}catch{}}var Rn=8e3,zn=5e3;function Bn(e,t,n,r){return new Promise((i,a)=>{let o=!1,s=n=>{o||(o=!0,clearTimeout(u),e.removeEventListener(t,c),e.removeEventListener(`error`,l),n?a(n):i())},c=()=>s(null),l=()=>s(Error(r)),u=setTimeout(()=>s(Error(r)),n);e.addEventListener(t,c,{once:!0}),e.addEventListener(`error`,l,{once:!0})})}function Vn(e,t){return new Promise((n,r)=>{let i=!1,a=t=>{i||(i=!0,clearTimeout(c),e.removeEventListener(`seeked`,o),e.removeEventListener(`error`,s),t?r(t):n())},o=()=>a(null),s=()=>a(Error(`视频跳帧失败`)),c=setTimeout(()=>a(Error(`视频跳帧超时`)),zn);e.addEventListener(`seeked`,o,{once:!0}),e.addEventListener(`error`,s,{once:!0}),e.currentTime=t})}function Hn(e,t,n){return new Promise((r,i)=>{let a=e.videoWidth,o=e.videoHeight;if(!a||!o)return i(Error(`无法读取视频尺寸`));let s=Math.min(1,t/a),c=document.createElement(`canvas`);c.width=Math.round(a*s),c.height=Math.round(o*s),c.getContext(`2d`).drawImage(e,0,0,c.width,c.height),c.toBlob(e=>e?r(e):i(Error(`画面导出失败`)),`image/jpeg`,n)})}function Un(e,t,n){if(t<=1){let t=e>0?Math.max(.05,e-.05):.05;return[Math.max(.05,Math.min(n,t))]}if(!e||e<=0)return Array.from({length:t},()=>.05);let r=e*.1,i=(e*.9-r)/(t-1);return Array.from({length:t},(e,t)=>r+i*t)}async function Wn(e,t={}){let{count:n=3,at:r=.1,maxWidth:i=1280,quality:a=.9}=t,o=URL.createObjectURL(e),s=document.createElement(`video`);s.preload=`auto`,s.muted=!0,s.playsInline=!0,s.src=o;try{await Bn(s,`loadeddata`,Rn,`视频加载超时,请换一个文件试试`);let e=[];for(let t of Un(s.duration||0,n,r))await Vn(s,t),e.push(await Hn(s,i,a));if(!e.length)throw Error(`未提取到有效画面`);return e}finally{URL.revokeObjectURL(o),s.removeAttribute(`src`)}}export{Mn as a,In as i,Wn as n,rn as o,Fn as r,Ln as t};