import{E as e,G as t,O as n,Z as r,s as i,v as a}from"./vue-vendor-VvR516j_.js";import{O as o,cn as s,dn as c,g as l,gn as u,h as d,m as f,mn as p,mt as m,p as h,pt as g,un as _}from"./initial-vendor-DGcJKj6B.js";import{t as v}from"./use-compitable-BRZdiTRV.js";function y(e){let{opacityDisabled:t,heightTiny:n,heightSmall:r,heightMedium:i,heightLarge:a,heightHuge:o,primaryColor:s,fontSize:c}=e;return{fontSize:c,textColor:s,sizeTiny:n,sizeSmall:r,sizeMedium:i,sizeLarge:a,sizeHuge:o,color:s,opacitySpinning:t}}var b={name:`Spin`,common:h,self:y},x=_([_(`@keyframes spin-rotate`,`
 from {
 transform: rotate(0);
 }
 to {
 transform: rotate(360deg);
 }
 `),c(`spin-container`,`
 position: relative;
 `,[c(`spin-body`,`
 position: absolute;
 top: 50%;
 left: 50%;
 transform: translateX(-50%) translateY(-50%);
 `,[f()])]),c(`spin-body`,`
 display: inline-flex;
 align-items: center;
 justify-content: center;
 flex-direction: column;
 `),c(`spin`,`
 display: inline-flex;
 height: var(--n-size);
 width: var(--n-size);
 font-size: var(--n-size);
 color: var(--n-color);
 `,[p(`rotate`,`
 animation: spin-rotate 2s linear infinite;
 `)]),c(`spin-description`,`
 display: inline-block;
 font-size: var(--n-font-size);
 color: var(--n-text-color);
 transition: color .3s var(--n-bezier);
 margin-top: 8px;
 `),c(`spin-content`,`
 opacity: 1;
 transition: opacity .3s var(--n-bezier);
 pointer-events: all;
 `,[p(`spinning`,`
 user-select: none;
 -webkit-user-select: none;
 pointer-events: none;
 opacity: var(--n-opacity-spinning);
 `)])]),S={small:20,medium:18,large:16},C=e({name:`Spin`,props:Object.assign(Object.assign(Object.assign({},o.props),{contentClass:String,contentStyle:[Object,String],description:String,size:{type:[String,Number],default:`medium`},show:{type:Boolean,default:!0},rotate:{type:Boolean,default:!0},spinning:{type:Boolean,validator:()=>!0,default:void 0},delay:Number}),l),slots:Object,setup(e){let{mergedClsPrefixRef:n,inlineThemeDisabled:i}=m(e),c=o(`Spin`,`-spin`,x,b,e,n),l=a(()=>{let{size:t}=e,{common:{cubicBezierEaseInOut:n},self:r}=c.value,{opacitySpinning:i,color:a,textColor:o}=r;return{"--n-bezier":n,"--n-opacity-spinning":i,"--n-size":typeof t==`number`?s(t):r[u(`size`,t)],"--n-color":a,"--n-text-color":o}}),d=i?g(`spin`,a(()=>{let{size:t}=e;return typeof t==`number`?String(t):t[0]}),l,e):void 0,f=v(e,[`spinning`,`show`]),p=r(!1);return t(t=>{let n;if(f.value){let{delay:r}=e;if(r){n=window.setTimeout(()=>{p.value=!0},r),t(()=>{clearTimeout(n)});return}}p.value=f.value}),{mergedClsPrefix:n,active:p,mergedStrokeWidth:a(()=>{let{strokeWidth:t}=e;if(t!==void 0)return t;let{size:n}=e;return S[typeof n==`number`?`medium`:n]}),cssVars:i?void 0:l,themeClass:d?.themeClass,onRender:d?.onRender}},render(){var e;let{$slots:t,mergedClsPrefix:r,description:a}=this,o=t.icon&&this.rotate,s=(a||t.description)&&n(`div`,{class:`${r}-spin-description`},a||t.description?.call(t)),c=t.icon?n(`div`,{class:[`${r}-spin-body`,this.themeClass]},n(`div`,{class:[`${r}-spin`,o&&`${r}-spin--rotate`],style:t.default?``:this.cssVars},t.icon()),s):n(`div`,{class:[`${r}-spin-body`,this.themeClass]},n(d,{clsPrefix:r,style:t.default?``:this.cssVars,stroke:this.stroke,"stroke-width":this.mergedStrokeWidth,radius:this.radius,scale:this.scale,class:`${r}-spin`}),s);return(e=this.onRender)==null||e.call(this),t.default?n(`div`,{class:[`${r}-spin-container`,this.themeClass],style:this.cssVars},n(`div`,{class:[`${r}-spin-content`,this.active&&`${r}-spin-content--spinning`,this.contentClass],style:this.contentStyle},t),n(i,{name:`fade-in-transition`},{default:()=>this.active?c:null})):c}});export{C as t};