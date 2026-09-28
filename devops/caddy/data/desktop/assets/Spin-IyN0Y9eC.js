import{$ as e,A as t,O as n,b as r,q as i,s as a}from"./vue-vendor-ZQDshSmE.js";import{O as o,cn as s,dn as c,g as l,gn as u,h as d,m as f,mn as p,mt as m,p as h,pt as g,un as _}from"./initial-vendor-CXHx5mAA.js";import{t as v}from"./use-compitable-BTP-85S-.js";function y(e){let{opacityDisabled:t,heightTiny:n,heightSmall:r,heightMedium:i,heightLarge:a,heightHuge:o,primaryColor:s,fontSize:c}=e;return{fontSize:c,textColor:s,sizeTiny:n,sizeSmall:r,sizeMedium:i,sizeLarge:a,sizeHuge:o,color:s,opacitySpinning:t}}var b={name:`Spin`,common:h,self:y},x=_([_(`@keyframes spin-rotate`,`
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
 `)])]),S={small:20,medium:18,large:16},C=n({name:`Spin`,props:Object.assign(Object.assign(Object.assign({},o.props),{contentClass:String,contentStyle:[Object,String],description:String,size:{type:[String,Number],default:`medium`},show:{type:Boolean,default:!0},rotate:{type:Boolean,default:!0},spinning:{type:Boolean,validator:()=>!0,default:void 0},delay:Number}),l),slots:Object,setup(t){let{mergedClsPrefixRef:n,inlineThemeDisabled:a}=m(t),c=o(`Spin`,`-spin`,x,b,t,n),l=r(()=>{let{size:e}=t,{common:{cubicBezierEaseInOut:n},self:r}=c.value,{opacitySpinning:i,color:a,textColor:o}=r;return{"--n-bezier":n,"--n-opacity-spinning":i,"--n-size":typeof e==`number`?s(e):r[u(`size`,e)],"--n-color":a,"--n-text-color":o}}),d=a?g(`spin`,r(()=>{let{size:e}=t;return typeof e==`number`?String(e):e[0]}),l,t):void 0,f=v(t,[`spinning`,`show`]),p=e(!1);return i(e=>{let n;if(f.value){let{delay:r}=t;if(r){n=window.setTimeout(()=>{p.value=!0},r),e(()=>{clearTimeout(n)});return}}p.value=f.value}),{mergedClsPrefix:n,active:p,mergedStrokeWidth:r(()=>{let{strokeWidth:e}=t;if(e!==void 0)return e;let{size:n}=t;return S[typeof n==`number`?`medium`:n]}),cssVars:a?void 0:l,themeClass:d?.themeClass,onRender:d?.onRender}},render(){var e;let{$slots:n,mergedClsPrefix:r,description:i}=this,o=n.icon&&this.rotate,s=(i||n.description)&&t(`div`,{class:`${r}-spin-description`},i||n.description?.call(n)),c=n.icon?t(`div`,{class:[`${r}-spin-body`,this.themeClass]},t(`div`,{class:[`${r}-spin`,o&&`${r}-spin--rotate`],style:n.default?``:this.cssVars},n.icon()),s):t(`div`,{class:[`${r}-spin-body`,this.themeClass]},t(d,{clsPrefix:r,style:n.default?``:this.cssVars,stroke:this.stroke,"stroke-width":this.mergedStrokeWidth,radius:this.radius,scale:this.scale,class:`${r}-spin`}),s);return(e=this.onRender)==null||e.call(this),n.default?t(`div`,{class:[`${r}-spin-container`,this.themeClass],style:this.cssVars},t(`div`,{class:[`${r}-spin-content`,this.active&&`${r}-spin-content--spinning`,this.contentClass],style:this.contentStyle},n),t(a,{name:`fade-in-transition`},{default:()=>this.active?c:null})):c}});export{C as t};