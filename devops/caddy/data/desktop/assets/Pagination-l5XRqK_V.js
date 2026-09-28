import{$ as e,A as t,F as n,H as r,K as i,L as a,N as o,O as s,P as c,R as l,Y as u,b as d,f,g as p,j as m,q as h,s as g,tt as _,z as v}from"./vue-vendor-ZQDshSmE.js";import{Bt as y,Ct as b,D as x,Dt as S,E as C,Ft as w,It as T,Mt as E,O as D,Rt as O,St as k,Xt as A,Zt as j,bt as M,cn as N,dn as P,en as F,f as I,ft as L,gn as R,gt as z,h as B,hn as V,in as H,j as U,l as W,ln as ee,mn as G,mt as K,on as q,p as J,pn as Y,pt as X,sn as te,u as ne,un as Z,vt as re,wt as Q,xt as $}from"./initial-vendor-CXHx5mAA.js";import{c as ie,d as ae,f as oe,g as se,i as ce,l as le,m as ue,n as de,p as fe,s as pe,t as me,u as he}from"./Popover-BbumLWk_.js";import{a as ge,i as _e,o as ve,r as ye,s as be,t as xe}from"./Tag-BfRiqgeS.js";import{t as Se}from"./use-merged-state-Doa9wl0w.js";import{t as Ce}from"./use-compitable-BTP-85S-.js";import{n as we}from"./Eye-DHQargfb.js";import{n as Te,r as Ee,t as De}from"./Input-B8Pp_Tpu.js";function Oe(e){return e&-e}var ke=class{constructor(e,t){this.l=e,this.min=t;let n=Array(e+1);for(let t=0;t<e+1;++t)n[t]=0;this.ft=n}add(e,t){if(t===0)return;let{l:n,ft:r}=this;for(e+=1;e<=n;)r[e]+=t,e+=Oe(e)}get(e){return this.sum(e+1)-this.sum(e)}sum(e){if(e===void 0&&(e=this.l),e<=0)return 0;let{ft:t,min:n,l:r}=this;if(e>r)throw Error("[FinweckTree.sum]: `i` is larger than length.");let i=e*n;for(;e>0;)i+=t[e],e-=Oe(e);return i}getBound(e){let t=0,n=this.l;for(;n>t;){let r=Math.floor((t+n)/2),i=this.sum(r);if(i>e){n=r;continue}else if(i<e){if(t===r)return this.sum(t+1)<=e?t+1:r;t=r}else return r}return t}},Ae;function je(){return typeof document>`u`?!1:(Ae===void 0&&(Ae=`matchMedia`in window?window.matchMedia(`(pointer:coarse)`).matches:!1),Ae)}var Me;function Ne(){return typeof document>`u`?1:(Me===void 0&&(Me=`chrome`in window?window.devicePixelRatio:1),Me)}var Pe=`VVirtualListXScroll`;function Fe({columnsRef:t,renderColRef:n,renderItemWithColsRef:i}){let a=e(0),o=e(0),s=d(()=>{let e=t.value;if(e.length===0)return null;let n=new ke(e.length,0);return e.forEach((e,t)=>{n.add(t,e.width)}),n});return r(Pe,{startIndexRef:F(()=>{let e=s.value;return e===null?0:Math.max(e.getBound(o.value)-1,0)}),endIndexRef:F(()=>{let e=s.value;return e===null?0:Math.min(e.getBound(o.value+a.value)+1,t.value.length-1)}),columnsRef:t,renderColRef:n,renderItemWithColsRef:i,getLeft:e=>{let t=s.value;return t===null?0:t.sum(e)}}),{listWidthRef:a,scrollLeftRef:o}}var Ie=s({name:`VirtualListRow`,props:{index:{type:Number,required:!0},item:{type:Object,required:!0}},setup(){let{startIndexRef:e,endIndexRef:t,columnsRef:n,getLeft:r,renderColRef:i,renderItemWithColsRef:a}=m(Pe);return{startIndex:e,endIndex:t,columns:n,renderCol:i,renderItemWithCols:a,getLeft:r}},render(){let{startIndex:e,endIndex:t,columns:n,renderCol:r,renderItemWithCols:i,getLeft:a,item:o}=this;if(i!=null)return i({itemIndex:this.index,startColIndex:e,endColIndex:t,allColumns:n,item:o,getLeft:a});if(r!=null){let i=[];for(let s=e;s<=t;++s){let e=n[s];i.push(r({column:e,left:a(s),item:o}))}return i}return null}}),Le=ie(`.v-vl`,{maxHeight:`inherit`,height:`100%`,overflow:`auto`,minWidth:`1px`},[ie(`&:not(.v-vl--show-scrollbar)`,{scrollbarWidth:`none`},[ie(`&::-webkit-scrollbar, &::-webkit-scrollbar-track-piece, &::-webkit-scrollbar-thumb`,{width:0,height:0,display:`none`})])]),Re=s({name:`VirtualList`,inheritAttrs:!1,props:{showScrollbar:{type:Boolean,default:!0},columns:{type:Array,default:()=>[]},renderCol:Function,renderItemWithCols:Function,items:{type:Array,default:()=>[]},itemSize:{type:Number,required:!0},itemResizable:Boolean,itemsStyle:[String,Object],visibleItemsTag:{type:[String,Object],default:`div`},visibleItemsProps:Object,ignoreItemResize:Boolean,onScroll:Function,onWheel:Function,onResize:Function,defaultScrollKey:[Number,String],defaultScrollIndex:Number,keyField:{type:String,default:`key`},paddingTop:{type:[Number,String],default:0},paddingBottom:{type:[Number,String],default:0}},setup(t){let r=O();Le.mount({id:`vueuc/virtual-list`,head:!0,anchorMetaName:le,ssr:r}),v(()=>{let{defaultScrollIndex:e,defaultScrollKey:n}=t;e==null?n!=null&&S({key:n}):S({index:e})});let i=!1,a=!1;n(()=>{if(i=!1,!a){a=!0;return}S({top:y.value,left:c.value})}),l(()=>{i=!0,a||=!0});let o=F(()=>{if(t.renderCol==null&&t.renderItemWithCols==null||t.columns.length===0)return;let e=0;return t.columns.forEach(t=>{e+=t.width}),e}),s=d(()=>{let e=new Map,{keyField:n}=t;return t.items.forEach((t,r)=>{e.set(t[n],r)}),e}),{scrollLeftRef:c,listWidthRef:u}=Fe({columnsRef:_(t,`columns`),renderColRef:_(t,`renderCol`),renderItemWithColsRef:_(t,`renderItemWithCols`)}),f=e(null),p=e(void 0),m=new Map,h=d(()=>{let{items:e,itemSize:n,keyField:r}=t,i=new ke(e.length,n);return e.forEach((e,t)=>{let n=e[r],a=m.get(n);a!==void 0&&i.add(t,a)}),i}),g=e(0),y=e(0),b=F(()=>Math.max(h.value.getBound(y.value-q(t.paddingTop))-1,0)),x=d(()=>{let{value:e}=p;if(e===void 0)return[];let{items:n,itemSize:r}=t,i=b.value,a=Math.min(i+Math.ceil(e/r+1),n.length-1),o=[];for(let e=i;e<=a;++e)o.push(n[e]);return o}),S=(e,t)=>{if(typeof e==`number`){E(e,t,`auto`);return}let{left:n,top:r,index:i,key:a,position:o,behavior:c,debounce:l=!0}=e;if(n!==void 0||r!==void 0)E(n,r,c);else if(i!==void 0)T(i,c,l);else if(a!==void 0){let e=s.value.get(a);e!==void 0&&T(e,c,l)}else o===`bottom`?E(0,2**53-1,c):o===`top`&&E(0,0,c)},C,w=null;function T(e,n,r){let{value:i}=h,a=i.sum(e)+q(t.paddingTop);if(!r)f.value.scrollTo({left:0,top:a,behavior:n});else{C=e,w!==null&&window.clearTimeout(w),w=window.setTimeout(()=>{C=void 0,w=null},16);let{scrollTop:t,offsetHeight:r}=f.value;if(a>t){let o=i.get(e);a+o<=t+r||f.value.scrollTo({left:0,top:a+o-r,behavior:n})}else f.value.scrollTo({left:0,top:a,behavior:n})}}function E(e,t,n){f.value.scrollTo({left:e,top:t,behavior:n})}function D(e,n){if(i||t.ignoreItemResize||L(n.target))return;let{value:r}=h,a=s.value.get(e),o=r.get(a),c=n.borderBoxSize?.[0]?.blockSize??n.contentRect.height;if(c===o)return;c-t.itemSize===0?m.delete(e):m.set(e,c-t.itemSize);let l=c-o;if(l===0)return;r.add(a,l);let u=f.value;if(u!=null){if(C===void 0){let e=r.sum(a);u.scrollTop>e&&u.scrollBy(0,l)}else (a<C||a===C&&c+r.sum(a)>u.scrollTop+u.offsetHeight)&&u.scrollBy(0,l);I()}g.value++}let k=!je(),A=!1;function j(e){var n;(n=t.onScroll)==null||n.call(t,e),(!k||!A)&&I()}function M(e){var n;if((n=t.onWheel)==null||n.call(t,e),k){let t=f.value;if(t!=null){if(e.deltaX===0&&(t.scrollTop===0&&e.deltaY<=0||t.scrollTop+t.offsetHeight>=t.scrollHeight&&e.deltaY>=0))return;e.preventDefault(),t.scrollTop+=e.deltaY/Ne(),t.scrollLeft+=e.deltaX/Ne(),I(),A=!0,se(()=>{A=!1})}}}function P(e){if(i||L(e.target))return;if(t.renderCol==null&&t.renderItemWithCols==null){if(e.contentRect.height===p.value)return}else if(e.contentRect.height===p.value&&e.contentRect.width===u.value)return;p.value=e.contentRect.height,u.value=e.contentRect.width;let{onResize:n}=t;n!==void 0&&n(e)}function I(){let{value:e}=f;e!=null&&(y.value=e.scrollTop,c.value=e.scrollLeft)}function L(e){let t=e;for(;t!==null;){if(t.style.display===`none`)return!0;t=t.parentElement}return!1}return{listHeight:p,listStyle:{overflow:`auto`},keyToIndex:s,itemsStyle:d(()=>{let{itemResizable:e}=t,n=N(h.value.sum());return g.value,[t.itemsStyle,{boxSizing:`content-box`,width:N(o.value),height:e?``:n,minHeight:e?n:``,paddingTop:N(t.paddingTop),paddingBottom:N(t.paddingBottom)}]}),visibleItemsStyle:d(()=>(g.value,{transform:`translateY(${N(h.value.sum(b.value))})`})),viewportItems:x,listElRef:f,itemsElRef:e(null),scrollTo:S,handleListResize:P,handleListScroll:j,handleListWheel:M,handleItemResize:D}},render(){let{itemResizable:e,keyField:n,keyToIndex:r,visibleItemsTag:i}=this;return t(w,{onResize:this.handleListResize},{default:()=>{var a;return t(`div`,o(this.$attrs,{class:[`v-vl`,this.showScrollbar&&`v-vl--show-scrollbar`],onScroll:this.handleListScroll,onWheel:this.handleListWheel,ref:`listElRef`}),[this.items.length===0?(a=this.$slots).empty?.call(a):t(`div`,{ref:`itemsElRef`,class:`v-vl-items`,style:this.itemsStyle},[t(i,Object.assign({class:`v-vl-visible-items`,style:this.visibleItemsStyle},this.visibleItemsProps),{default:()=>{let{renderCol:i,renderItemWithCols:a}=this;return this.viewportItems.map(o=>{let s=o[n],c=r.get(s),l=i==null?void 0:t(Ie,{index:c,item:o}),u=a==null?void 0:t(Ie,{index:c,item:o}),d=this.$slots.default({item:o,renderedCols:l,renderedItemWithCols:u,index:c})[0];return e?t(w,{key:s,onResize:e=>this.handleItemResize(s,e)},{default:()=>d}):(d.key=s,d)})}})])])}})}});function ze(e,t){t&&(v(()=>{let{value:n}=e;n&&T.registerHandler(n,t)}),i(e,(e,t)=>{t&&T.unregisterHandler(t)},{deep:!1}),a(()=>{let{value:t}=e;t&&T.unregisterHandler(t)}))}function Be(e){switch(typeof e){case`string`:return e||void 0;case`number`:return String(e);default:return}}var Ve={tiny:`mini`,small:`tiny`,medium:`small`,large:`medium`,huge:`large`};function He(e){let t=Ve[e];if(t===void 0)throw Error(`${e} has no smaller size.`);return t}function Ue(e){let t=e.filter(e=>e!==void 0);if(t.length!==0)return t.length===1?t[0]:t=>{e.forEach(e=>{e&&e(t)})}}var We=s({name:`Backward`,render(){return t(`svg`,{viewBox:`0 0 20 20`,fill:`none`,xmlns:`http://www.w3.org/2000/svg`},t(`path`,{d:`M12.2674 15.793C11.9675 16.0787 11.4927 16.0672 11.2071 15.7673L6.20572 10.5168C5.9298 10.2271 5.9298 9.7719 6.20572 9.48223L11.2071 4.23177C11.4927 3.93184 11.9675 3.92031 12.2674 4.206C12.5673 4.49169 12.5789 4.96642 12.2932 5.26634L7.78458 9.99952L12.2932 14.7327C12.5789 15.0326 12.5673 15.5074 12.2674 15.793Z`,fill:`currentColor`}))}}),Ge=s({name:`Checkmark`,render(){return t(`svg`,{xmlns:`http://www.w3.org/2000/svg`,viewBox:`0 0 16 16`},t(`g`,{fill:`none`},t(`path`,{d:`M14.046 3.486a.75.75 0 0 1-.032 1.06l-7.93 7.474a.85.85 0 0 1-1.188-.022l-2.68-2.72a.75.75 0 1 1 1.068-1.053l2.234 2.267l7.468-7.038a.75.75 0 0 1 1.06.032z`,fill:`currentColor`})))}}),Ke=s({name:`Empty`,render(){return t(`svg`,{viewBox:`0 0 28 28`,fill:`none`,xmlns:`http://www.w3.org/2000/svg`},t(`path`,{d:`M26 7.5C26 11.0899 23.0899 14 19.5 14C15.9101 14 13 11.0899 13 7.5C13 3.91015 15.9101 1 19.5 1C23.0899 1 26 3.91015 26 7.5ZM16.8536 4.14645C16.6583 3.95118 16.3417 3.95118 16.1464 4.14645C15.9512 4.34171 15.9512 4.65829 16.1464 4.85355L18.7929 7.5L16.1464 10.1464C15.9512 10.3417 15.9512 10.6583 16.1464 10.8536C16.3417 11.0488 16.6583 11.0488 16.8536 10.8536L19.5 8.20711L22.1464 10.8536C22.3417 11.0488 22.6583 11.0488 22.8536 10.8536C23.0488 10.6583 23.0488 10.3417 22.8536 10.1464L20.2071 7.5L22.8536 4.85355C23.0488 4.65829 23.0488 4.34171 22.8536 4.14645C22.6583 3.95118 22.3417 3.95118 22.1464 4.14645L19.5 6.79289L16.8536 4.14645Z`,fill:`currentColor`}),t(`path`,{d:`M25 22.75V12.5991C24.5572 13.0765 24.053 13.4961 23.5 13.8454V16H17.5L17.3982 16.0068C17.0322 16.0565 16.75 16.3703 16.75 16.75C16.75 18.2688 15.5188 19.5 14 19.5C12.4812 19.5 11.25 18.2688 11.25 16.75L11.2432 16.6482C11.1935 16.2822 10.8797 16 10.5 16H4.5V7.25C4.5 6.2835 5.2835 5.5 6.25 5.5H12.2696C12.4146 4.97463 12.6153 4.47237 12.865 4H6.25C4.45507 4 3 5.45507 3 7.25V22.75C3 24.5449 4.45507 26 6.25 26H21.75C23.5449 26 25 24.5449 25 22.75ZM4.5 22.75V17.5H9.81597L9.85751 17.7041C10.2905 19.5919 11.9808 21 14 21L14.215 20.9947C16.2095 20.8953 17.842 19.4209 18.184 17.5H23.5V22.75C23.5 23.7165 22.7165 24.5 21.75 24.5H6.25C5.2835 24.5 4.5 23.7165 4.5 22.75Z`,fill:`currentColor`}))}}),qe=s({name:`FastBackward`,render(){return t(`svg`,{viewBox:`0 0 20 20`,version:`1.1`,xmlns:`http://www.w3.org/2000/svg`},t(`g`,{stroke:`none`,"stroke-width":`1`,fill:`none`,"fill-rule":`evenodd`},t(`g`,{fill:`currentColor`,"fill-rule":`nonzero`},t(`path`,{d:`M8.73171,16.7949 C9.03264,17.0795 9.50733,17.0663 9.79196,16.7654 C10.0766,16.4644 10.0634,15.9897 9.76243,15.7051 L4.52339,10.75 L17.2471,10.75 C17.6613,10.75 17.9971,10.4142 17.9971,10 C17.9971,9.58579 17.6613,9.25 17.2471,9.25 L4.52112,9.25 L9.76243,4.29275 C10.0634,4.00812 10.0766,3.53343 9.79196,3.2325 C9.50733,2.93156 9.03264,2.91834 8.73171,3.20297 L2.31449,9.27241 C2.14819,9.4297 2.04819,9.62981 2.01448,9.8386 C2.00308,9.89058 1.99707,9.94459 1.99707,10 C1.99707,10.0576 2.00356,10.1137 2.01585,10.1675 C2.05084,10.3733 2.15039,10.5702 2.31449,10.7254 L8.73171,16.7949 Z`}))))}}),Je=s({name:`FastForward`,render(){return t(`svg`,{viewBox:`0 0 20 20`,version:`1.1`,xmlns:`http://www.w3.org/2000/svg`},t(`g`,{stroke:`none`,"stroke-width":`1`,fill:`none`,"fill-rule":`evenodd`},t(`g`,{fill:`currentColor`,"fill-rule":`nonzero`},t(`path`,{d:`M11.2654,3.20511 C10.9644,2.92049 10.4897,2.93371 10.2051,3.23464 C9.92049,3.53558 9.93371,4.01027 10.2346,4.29489 L15.4737,9.25 L2.75,9.25 C2.33579,9.25 2,9.58579 2,10.0000012 C2,10.4142 2.33579,10.75 2.75,10.75 L15.476,10.75 L10.2346,15.7073 C9.93371,15.9919 9.92049,16.4666 10.2051,16.7675 C10.4897,17.0684 10.9644,17.0817 11.2654,16.797 L17.6826,10.7276 C17.8489,10.5703 17.9489,10.3702 17.9826,10.1614 C17.994,10.1094 18,10.0554 18,10.0000012 C18,9.94241 17.9935,9.88633 17.9812,9.83246 C17.9462,9.62667 17.8467,9.42976 17.6826,9.27455 L11.2654,3.20511 Z`}))))}}),Ye=s({name:`Forward`,render(){return t(`svg`,{viewBox:`0 0 20 20`,fill:`none`,xmlns:`http://www.w3.org/2000/svg`},t(`path`,{d:`M7.73271 4.20694C8.03263 3.92125 8.50737 3.93279 8.79306 4.23271L13.7944 9.48318C14.0703 9.77285 14.0703 10.2281 13.7944 10.5178L8.79306 15.7682C8.50737 16.0681 8.03263 16.0797 7.73271 15.794C7.43279 15.5083 7.42125 15.0336 7.70694 14.7336L12.2155 10.0005L7.70694 5.26729C7.42125 4.96737 7.43279 4.49264 7.73271 4.20694Z`,fill:`currentColor`}))}}),Xe=s({name:`More`,render(){return t(`svg`,{viewBox:`0 0 16 16`,version:`1.1`,xmlns:`http://www.w3.org/2000/svg`},t(`g`,{stroke:`none`,"stroke-width":`1`,fill:`none`,"fill-rule":`evenodd`},t(`g`,{fill:`currentColor`,"fill-rule":`nonzero`},t(`path`,{d:`M4,7 C4.55228,7 5,7.44772 5,8 C5,8.55229 4.55228,9 4,9 C3.44772,9 3,8.55229 3,8 C3,7.44772 3.44772,7 4,7 Z M8,7 C8.55229,7 9,7.44772 9,8 C9,8.55229 8.55229,9 8,9 C7.44772,9 7,8.55229 7,8 C7,7.44772 7.44772,7 8,7 Z M12,7 C12.5523,7 13,7.44772 13,8 C13,8.55229 12.5523,9 12,9 C11.4477,9 11,8.55229 11,8 C11,7.44772 11.4477,7 12,7 Z`}))))}}),Ze=s({props:{onFocus:Function,onBlur:Function},setup(e){return()=>t(`div`,{style:`width: 0; height: 0`,tabindex:0,onFocus:e.onFocus,onBlur:e.onBlur})}}),Qe={iconSizeTiny:`28px`,iconSizeSmall:`34px`,iconSizeMedium:`40px`,iconSizeLarge:`46px`,iconSizeHuge:`52px`};function $e(e){let{textColorDisabled:t,iconColor:n,textColor2:r,fontSizeTiny:i,fontSizeSmall:a,fontSizeMedium:o,fontSizeLarge:s,fontSizeHuge:c}=e;return Object.assign(Object.assign({},Qe),{fontSizeTiny:i,fontSizeSmall:a,fontSizeMedium:o,fontSizeLarge:s,fontSizeHuge:c,textColor:t,iconColor:n,extraTextColor:r})}var et={name:`Empty`,common:J,self:$e},tt=P(`empty`,`
 display: flex;
 flex-direction: column;
 align-items: center;
 font-size: var(--n-font-size);
`,[Y(`icon`,`
 width: var(--n-icon-size);
 height: var(--n-icon-size);
 font-size: var(--n-icon-size);
 line-height: var(--n-icon-size);
 color: var(--n-icon-color);
 transition:
 color .3s var(--n-bezier);
 `,[Z(`+`,[Y(`description`,`
 margin-top: 8px;
 `)])]),Y(`description`,`
 transition: color .3s var(--n-bezier);
 color: var(--n-text-color);
 `),Y(`extra`,`
 text-align: center;
 transition: color .3s var(--n-bezier);
 margin-top: 12px;
 color: var(--n-extra-text-color);
 `)]),nt=s({name:`Empty`,props:Object.assign(Object.assign({},D.props),{description:String,showDescription:{type:Boolean,default:!0},showIcon:{type:Boolean,default:!0},size:{type:String,default:`medium`},renderIcon:Function}),slots:Object,setup(e){let{mergedClsPrefixRef:n,inlineThemeDisabled:r,mergedComponentPropsRef:i}=K(e),a=D(`Empty`,`-empty`,tt,et,e,n),{localeRef:o}=we(`Empty`),s=d(()=>e.description??i?.value?.Empty?.description),c=d(()=>i?.value?.Empty?.renderIcon||(()=>t(Ke,null))),l=d(()=>{let{size:t}=e,{common:{cubicBezierEaseInOut:n},self:{[R(`iconSize`,t)]:r,[R(`fontSize`,t)]:i,textColor:o,iconColor:s,extraTextColor:c}}=a.value;return{"--n-icon-size":r,"--n-font-size":i,"--n-bezier":n,"--n-text-color":o,"--n-icon-color":s,"--n-extra-text-color":c}}),u=r?X(`empty`,d(()=>{let t=``,{size:n}=e;return t+=n[0],t}),l,e):void 0;return{mergedClsPrefix:n,mergedRenderIcon:c,localizedDescription:d(()=>s.value||o.value.description),cssVars:r?void 0:l,themeClass:u?.themeClass,onRender:u?.onRender}},render(){let{$slots:e,mergedClsPrefix:n,onRender:r}=this;return r?.(),t(`div`,{class:[`${n}-empty`,this.themeClass],style:this.cssVars},this.showIcon?t(`div`,{class:`${n}-empty__icon`},e.icon?e.icon():t(C,{clsPrefix:n},{default:this.mergedRenderIcon})):null,this.showDescription?t(`div`,{class:`${n}-empty__description`},e.default?e.default():this.localizedDescription):null,e.extra?t(`div`,{class:`${n}-empty__extra`},e.extra()):null)}}),rt={height:`calc(var(--n-option-height) * 7.6)`,paddingTiny:`4px 0`,paddingSmall:`4px 0`,paddingMedium:`4px 0`,paddingLarge:`4px 0`,paddingHuge:`4px 0`,optionPaddingTiny:`0 12px`,optionPaddingSmall:`0 12px`,optionPaddingMedium:`0 12px`,optionPaddingLarge:`0 12px`,optionPaddingHuge:`0 12px`,loadingSize:`18px`};function it(e){let{borderRadius:t,popoverColor:n,textColor3:r,dividerColor:i,textColor2:a,primaryColorPressed:o,textColorDisabled:s,primaryColor:c,opacityDisabled:l,hoverColor:u,fontSizeTiny:d,fontSizeSmall:f,fontSizeMedium:p,fontSizeLarge:m,fontSizeHuge:h,heightTiny:g,heightSmall:_,heightMedium:v,heightLarge:y,heightHuge:b}=e;return Object.assign(Object.assign({},rt),{optionFontSizeTiny:d,optionFontSizeSmall:f,optionFontSizeMedium:p,optionFontSizeLarge:m,optionFontSizeHuge:h,optionHeightTiny:g,optionHeightSmall:_,optionHeightMedium:v,optionHeightLarge:y,optionHeightHuge:b,borderRadius:t,color:n,groupHeaderTextColor:r,actionDividerColor:i,optionTextColor:a,optionTextColorPressed:o,optionTextColorDisabled:s,optionTextColorActive:c,optionOpacityDisabled:l,optionCheckColor:c,optionColorPending:u,optionColorActive:`rgba(0, 0, 0, 0)`,optionColorActivePending:u,actionTextColor:a,loadingColor:c})}var at=x({name:`InternalSelectMenu`,common:J,peers:{Scrollbar:I,Empty:et},self:it}),ot=s({name:`NBaseSelectGroupHeader`,props:{clsPrefix:{type:String,required:!0},tmNode:{type:Object,required:!0}},setup(){let{renderLabelRef:e,renderOptionRef:t,labelFieldRef:n,nodePropsRef:r}=m(ue);return{labelField:n,nodeProps:r,renderLabel:e,renderOption:t}},render(){let{clsPrefix:e,renderLabel:n,renderOption:r,nodeProps:i,tmNode:{rawNode:a}}=this,o=i?.(a),s=n?n(a,!1):$(a[this.labelField],a,!1),c=t(`div`,Object.assign({},o,{class:[`${e}-base-select-group-header`,o?.class]}),s);return a.render?a.render({node:c,option:a}):r?r({node:c,option:a,selected:!1}):c}});function st(e,n){return t(g,{name:`fade-in-scale-up-transition`},{default:()=>e?t(C,{clsPrefix:n,class:`${n}-base-select-option__check`},{default:()=>t(Ge)}):null})}var ct=s({name:`NBaseSelectOption`,props:{clsPrefix:{type:String,required:!0},tmNode:{type:Object,required:!0}},setup(e){let{valueRef:t,pendingTmNodeRef:n,multipleRef:r,valueSetRef:i,renderLabelRef:a,renderOptionRef:o,labelFieldRef:s,valueFieldRef:c,showCheckmarkRef:l,nodePropsRef:u,handleOptionClick:d,handleOptionMouseEnter:f}=m(ue),p=F(()=>{let{value:t}=n;return t?e.tmNode.key===t.key:!1});function h(t){let{tmNode:n}=e;n.disabled||d(t,n)}function g(t){let{tmNode:n}=e;n.disabled||f(t,n)}function _(t){let{tmNode:n}=e,{value:r}=p;n.disabled||r||f(t,n)}return{multiple:r,isGrouped:F(()=>{let{tmNode:t}=e,{parent:n}=t;return n&&n.rawNode.type===`group`}),showCheckmark:l,nodeProps:u,isPending:p,isSelected:F(()=>{let{value:n}=t,{value:a}=r;if(n===null)return!1;let o=e.tmNode.rawNode[c.value];if(a){let{value:e}=i;return e.has(o)}else return n===o}),labelField:s,renderLabel:a,renderOption:o,handleMouseMove:_,handleMouseEnter:g,handleClick:h}},render(){let{clsPrefix:e,tmNode:{rawNode:n},isSelected:r,isPending:i,isGrouped:a,showCheckmark:o,nodeProps:s,renderOption:c,renderLabel:l,handleClick:u,handleMouseEnter:d,handleMouseMove:f}=this,p=st(r,e),m=l?[l(n,r),o&&p]:[$(n[this.labelField],n,r),o&&p],h=s?.(n),g=t(`div`,Object.assign({},h,{class:[`${e}-base-select-option`,n.class,h?.class,{[`${e}-base-select-option--disabled`]:n.disabled,[`${e}-base-select-option--selected`]:r,[`${e}-base-select-option--grouped`]:a,[`${e}-base-select-option--pending`]:i,[`${e}-base-select-option--show-checkmark`]:o}],style:[h?.style||``,n.style||``],onClick:Ue([u,h?.onClick]),onMouseenter:Ue([d,h?.onMouseenter]),onMousemove:Ue([f,h?.onMousemove])}),t(`div`,{class:`${e}-base-select-option__content`},m));return n.render?n.render({node:g,option:n,selected:r}):c?c({node:g,option:n,selected:r}):g}}),lt=P(`base-select-menu`,`
 line-height: 1.5;
 outline: none;
 z-index: 0;
 position: relative;
 border-radius: var(--n-border-radius);
 transition:
 background-color .3s var(--n-bezier),
 box-shadow .3s var(--n-bezier);
 background-color: var(--n-color);
`,[P(`scrollbar`,`
 max-height: var(--n-height);
 `),P(`virtual-list`,`
 max-height: var(--n-height);
 `),P(`base-select-option`,`
 min-height: var(--n-option-height);
 font-size: var(--n-option-font-size);
 display: flex;
 align-items: center;
 `,[Y(`content`,`
 z-index: 1;
 white-space: nowrap;
 text-overflow: ellipsis;
 overflow: hidden;
 `)]),P(`base-select-group-header`,`
 min-height: var(--n-option-height);
 font-size: .93em;
 display: flex;
 align-items: center;
 `),P(`base-select-menu-option-wrapper`,`
 position: relative;
 width: 100%;
 `),Y(`loading, empty`,`
 display: flex;
 padding: 12px 32px;
 flex: 1;
 justify-content: center;
 `),Y(`loading`,`
 color: var(--n-loading-color);
 font-size: var(--n-loading-size);
 `),Y(`header`,`
 padding: 8px var(--n-option-padding-left);
 font-size: var(--n-option-font-size);
 transition: 
 color .3s var(--n-bezier),
 border-color .3s var(--n-bezier);
 border-bottom: 1px solid var(--n-action-divider-color);
 color: var(--n-action-text-color);
 `),Y(`action`,`
 padding: 8px var(--n-option-padding-left);
 font-size: var(--n-option-font-size);
 transition: 
 color .3s var(--n-bezier),
 border-color .3s var(--n-bezier);
 border-top: 1px solid var(--n-action-divider-color);
 color: var(--n-action-text-color);
 `),P(`base-select-group-header`,`
 position: relative;
 cursor: default;
 padding: var(--n-option-padding);
 color: var(--n-group-header-text-color);
 `),P(`base-select-option`,`
 cursor: pointer;
 position: relative;
 padding: var(--n-option-padding);
 transition:
 color .3s var(--n-bezier),
 opacity .3s var(--n-bezier);
 box-sizing: border-box;
 color: var(--n-option-text-color);
 opacity: 1;
 `,[G(`show-checkmark`,`
 padding-right: calc(var(--n-option-padding-right) + 20px);
 `),Z(`&::before`,`
 content: "";
 position: absolute;
 left: 4px;
 right: 4px;
 top: 0;
 bottom: 0;
 border-radius: var(--n-border-radius);
 transition: background-color .3s var(--n-bezier);
 `),Z(`&:active`,`
 color: var(--n-option-text-color-pressed);
 `),G(`grouped`,`
 padding-left: calc(var(--n-option-padding-left) * 1.5);
 `),G(`pending`,[Z(`&::before`,`
 background-color: var(--n-option-color-pending);
 `)]),G(`selected`,`
 color: var(--n-option-text-color-active);
 `,[Z(`&::before`,`
 background-color: var(--n-option-color-active);
 `),G(`pending`,[Z(`&::before`,`
 background-color: var(--n-option-color-active-pending);
 `)])]),G(`disabled`,`
 cursor: not-allowed;
 `,[V(`selected`,`
 color: var(--n-option-text-color-disabled);
 `),G(`selected`,`
 opacity: var(--n-option-opacity-disabled);
 `)]),Y(`check`,`
 font-size: 16px;
 position: absolute;
 right: calc(var(--n-option-padding-right) - 4px);
 top: calc(50% - 7px);
 color: var(--n-option-check-color);
 transition: color .3s var(--n-bezier);
 `,[W({enterScale:`0.5`})])])]),ut=s({name:`InternalSelectMenu`,props:Object.assign(Object.assign({},D.props),{clsPrefix:{type:String,required:!0},scrollable:{type:Boolean,default:!0},treeMate:{type:Object,required:!0},multiple:Boolean,size:{type:String,default:`medium`},value:{type:[String,Number,Array],default:null},autoPending:Boolean,virtualScroll:{type:Boolean,default:!0},show:{type:Boolean,default:!0},labelField:{type:String,default:`label`},valueField:{type:String,default:`value`},loading:Boolean,focusable:Boolean,renderLabel:Function,renderOption:Function,nodeProps:Function,showCheckmark:{type:Boolean,default:!0},onMousedown:Function,onScroll:Function,onFocus:Function,onBlur:Function,onKeyup:Function,onKeydown:Function,onTabOut:Function,onMouseenter:Function,onMouseleave:Function,onResize:Function,resetMenuOnOptionsChange:{type:Boolean,default:!0},inlineThemeDisabled:Boolean,scrollbarProps:Object,onToggle:Function}),setup(t){let{mergedClsPrefixRef:n,mergedRtlRef:o,mergedComponentPropsRef:s}=K(t),l=U(`InternalSelectMenu`,o,n),u=D(`InternalSelectMenu`,`-internal-select-menu`,lt,at,t,_(t,`clsPrefix`)),f=e(null),p=e(null),m=e(null),h=d(()=>t.treeMate.getFlattenedNodes()),g=d(()=>_e(h.value)),y=e(null);function b(){let{treeMate:e}=t,n=null,{value:r}=t;r===null?n=e.getFirstAvailableNode():(n=t.multiple?e.getNode((r||[])[(r||[]).length-1]):e.getNode(r),(!n||n.disabled)&&(n=e.getFirstAvailableNode())),H(n||null)}function x(){let{value:e}=y;e&&!t.treeMate.getNode(e.key)&&(y.value=null)}let S;i(()=>t.show,e=>{e?S=i(()=>t.treeMate,()=>{t.resetMenuOnOptionsChange?(t.autoPending?b():x(),c(W)):x()},{immediate:!0}):S?.()},{immediate:!0}),a(()=>{S?.()});let C=d(()=>q(u.value.self[R(`optionHeight`,t.size)])),w=d(()=>te(u.value.self[R(`padding`,t.size)])),T=d(()=>t.multiple&&Array.isArray(t.value)?new Set(t.value):new Set),E=d(()=>{let e=h.value;return e&&e.length===0}),O=d(()=>s?.value?.Select?.renderEmpty);function k(e){let{onToggle:n}=t;n&&n(e)}function A(e){let{onScroll:n}=t;n&&n(e)}function j(e){var t;(t=m.value)==null||t.sync(),A(e)}function M(){var e;(e=m.value)==null||e.sync()}function N(){let{value:e}=y;return e||null}function P(e,t){t.disabled||H(t,!1)}function F(e,t){t.disabled||k(t)}function I(e){var n;be(e,`action`)||(n=t.onKeyup)==null||n.call(t,e)}function L(e){var n;be(e,`action`)||(n=t.onKeydown)==null||n.call(t,e)}function z(e){var n;(n=t.onMousedown)==null||n.call(t,e),!t.focusable&&e.preventDefault()}function B(){let{value:e}=y;e&&H(e.getNext({loop:!0}),!0)}function V(){let{value:e}=y;e&&H(e.getPrev({loop:!0}),!0)}function H(e,t=!1){y.value=e,t&&W()}function W(){var e,n;let r=y.value;if(!r)return;let i=g.value(r.key);i!==null&&(t.virtualScroll?(e=p.value)==null||e.scrollTo({index:i}):(n=m.value)==null||n.scrollTo({index:i,elSize:C.value}))}function ee(e){var n;f.value?.contains(e.target)&&((n=t.onFocus)==null||n.call(t,e))}function G(e){var n;f.value?.contains(e.relatedTarget)||(n=t.onBlur)==null||n.call(t,e)}r(ue,{handleOptionMouseEnter:P,handleOptionClick:F,valueSetRef:T,pendingTmNodeRef:y,nodePropsRef:_(t,`nodeProps`),showCheckmarkRef:_(t,`showCheckmark`),multipleRef:_(t,`multiple`),valueRef:_(t,`value`),renderLabelRef:_(t,`renderLabel`),renderOptionRef:_(t,`renderOption`),labelFieldRef:_(t,`labelField`),valueFieldRef:_(t,`valueField`)}),r(fe,f),v(()=>{let{value:e}=m;e&&e.sync()});let J=d(()=>{let{size:e}=t,{common:{cubicBezierEaseInOut:n},self:{height:r,borderRadius:i,color:a,groupHeaderTextColor:o,actionDividerColor:s,optionTextColorPressed:c,optionTextColor:l,optionTextColorDisabled:d,optionTextColorActive:f,optionOpacityDisabled:p,optionCheckColor:m,actionTextColor:h,optionColorPending:g,optionColorActive:_,loadingColor:v,loadingSize:y,optionColorActivePending:b,[R(`optionFontSize`,e)]:x,[R(`optionHeight`,e)]:S,[R(`optionPadding`,e)]:C}}=u.value;return{"--n-height":r,"--n-action-divider-color":s,"--n-action-text-color":h,"--n-bezier":n,"--n-border-radius":i,"--n-color":a,"--n-option-font-size":x,"--n-group-header-text-color":o,"--n-option-check-color":m,"--n-option-color-pending":g,"--n-option-color-active":_,"--n-option-color-active-pending":b,"--n-option-height":S,"--n-option-opacity-disabled":p,"--n-option-text-color":l,"--n-option-text-color-active":f,"--n-option-text-color-disabled":d,"--n-option-text-color-pressed":c,"--n-option-padding":C,"--n-option-padding-left":te(C,`left`),"--n-option-padding-right":te(C,`right`),"--n-loading-color":v,"--n-loading-size":y}}),{inlineThemeDisabled:Y}=t,ne=Y?X(`internal-select-menu`,d(()=>t.size[0]),J,t):void 0,Z={selfRef:f,next:B,prev:V,getPendingTmNode:N};return ze(f,t.onResize),Object.assign({mergedTheme:u,mergedClsPrefix:n,rtlEnabled:l,virtualListRef:p,scrollbarRef:m,itemSize:C,padding:w,flattenedNodes:h,empty:E,mergedRenderEmpty:O,virtualListContainer(){let{value:e}=p;return e?.listElRef},virtualListContent(){let{value:e}=p;return e?.itemsElRef},doScroll:A,handleFocusin:ee,handleFocusout:G,handleKeyUp:I,handleKeyDown:L,handleMouseDown:z,handleVirtualListResize:M,handleVirtualListScroll:j,cssVars:Y?void 0:J,themeClass:ne?.themeClass,onRender:ne?.onRender},Z)},render(){let{$slots:e,virtualScroll:n,clsPrefix:r,mergedTheme:i,themeClass:a,onRender:o}=this;return o?.(),t(`div`,{ref:`selfRef`,tabindex:this.focusable?0:-1,class:[`${r}-base-select-menu`,`${r}-base-select-menu--${this.size}-size`,this.rtlEnabled&&`${r}-base-select-menu--rtl`,a,this.multiple&&`${r}-base-select-menu--multiple`],style:this.cssVars,onFocusin:this.handleFocusin,onFocusout:this.handleFocusout,onKeyup:this.handleKeyUp,onKeydown:this.handleKeyDown,onMousedown:this.handleMouseDown,onMouseenter:this.onMouseenter,onMouseleave:this.onMouseleave},M(e.header,e=>e&&t(`div`,{class:`${r}-base-select-menu__header`,"data-header":!0,key:`header`},e)),this.loading?t(`div`,{class:`${r}-base-select-menu__loading`},t(B,{clsPrefix:r,strokeWidth:20})):this.empty?t(`div`,{class:`${r}-base-select-menu__empty`,"data-empty":!0},re(e.empty,()=>[this.mergedRenderEmpty?.call(this)||t(nt,{theme:i.peers.Empty,themeOverrides:i.peerOverrides.Empty,size:this.size})])):t(ne,Object.assign({ref:`scrollbarRef`,theme:i.peers.Scrollbar,themeOverrides:i.peerOverrides.Scrollbar,scrollable:this.scrollable,container:n?this.virtualListContainer:void 0,content:n?this.virtualListContent:void 0,onScroll:n?void 0:this.doScroll},this.scrollbarProps),{default:()=>n?t(Re,{ref:`virtualListRef`,class:`${r}-virtual-list`,items:this.flattenedNodes,itemSize:this.itemSize,showScrollbar:!1,paddingTop:this.padding.top,paddingBottom:this.padding.bottom,onResize:this.handleVirtualListResize,onScroll:this.handleVirtualListScroll,itemResizable:!0},{default:({item:e})=>e.isGroup?t(ot,{key:e.key,clsPrefix:r,tmNode:e}):e.ignored?null:t(ct,{clsPrefix:r,key:e.key,tmNode:e})}):t(`div`,{class:`${r}-base-select-menu-option-wrapper`,style:{paddingTop:this.padding.top,paddingBottom:this.padding.bottom}},this.flattenedNodes.map(e=>e.isGroup?t(ot,{key:e.key,clsPrefix:r,tmNode:e}):t(ct,{clsPrefix:r,key:e.key,tmNode:e})))}),M(e.action,e=>e&&[t(`div`,{class:`${r}-base-select-menu__action`,"data-action":!0,key:`action`},e),t(Ze,{onFocus:this.onTabOut,key:`focus-detector`})]))}}),dt={paddingSingle:`0 26px 0 12px`,paddingMultiple:`3px 26px 0 12px`,clearSize:`16px`,arrowSize:`16px`};function ft(e){let{borderRadius:t,textColor2:n,textColorDisabled:r,inputColor:i,inputColorDisabled:a,primaryColor:o,primaryColorHover:s,warningColor:c,warningColorHover:l,errorColor:u,errorColorHover:d,borderColor:f,iconColor:p,iconColorDisabled:m,clearColor:h,clearColorHover:g,clearColorPressed:_,placeholderColor:v,placeholderColorDisabled:y,fontSizeTiny:b,fontSizeSmall:x,fontSizeMedium:S,fontSizeLarge:C,heightTiny:w,heightSmall:T,heightMedium:E,heightLarge:D,fontWeight:O}=e;return Object.assign(Object.assign({},dt),{fontSizeTiny:b,fontSizeSmall:x,fontSizeMedium:S,fontSizeLarge:C,heightTiny:w,heightSmall:T,heightMedium:E,heightLarge:D,borderRadius:t,fontWeight:O,textColor:n,textColorDisabled:r,placeholderColor:v,placeholderColorDisabled:y,color:i,colorDisabled:a,colorActive:i,border:`1px solid ${f}`,borderHover:`1px solid ${s}`,borderActive:`1px solid ${o}`,borderFocus:`1px solid ${s}`,boxShadowHover:`none`,boxShadowActive:`0 0 0 2px ${H(o,{alpha:.2})}`,boxShadowFocus:`0 0 0 2px ${H(o,{alpha:.2})}`,caretColor:o,arrowColor:p,arrowColorDisabled:m,loadingColor:o,borderWarning:`1px solid ${c}`,borderHoverWarning:`1px solid ${l}`,borderActiveWarning:`1px solid ${c}`,borderFocusWarning:`1px solid ${l}`,boxShadowHoverWarning:`none`,boxShadowActiveWarning:`0 0 0 2px ${H(c,{alpha:.2})}`,boxShadowFocusWarning:`0 0 0 2px ${H(c,{alpha:.2})}`,colorActiveWarning:i,caretColorWarning:c,borderError:`1px solid ${u}`,borderHoverError:`1px solid ${d}`,borderActiveError:`1px solid ${u}`,borderFocusError:`1px solid ${d}`,boxShadowHoverError:`none`,boxShadowActiveError:`0 0 0 2px ${H(u,{alpha:.2})}`,boxShadowFocusError:`0 0 0 2px ${H(u,{alpha:.2})}`,colorActiveError:i,caretColorError:u,clearColor:h,clearColorHover:g,clearColorPressed:_})}var pt=x({name:`InternalSelection`,common:J,peers:{Popover:ce},self:ft}),mt=Z([P(`base-selection`,`
 --n-padding-single: var(--n-padding-single-top) var(--n-padding-single-right) var(--n-padding-single-bottom) var(--n-padding-single-left);
 --n-padding-multiple: var(--n-padding-multiple-top) var(--n-padding-multiple-right) var(--n-padding-multiple-bottom) var(--n-padding-multiple-left);
 position: relative;
 z-index: auto;
 box-shadow: none;
 width: 100%;
 max-width: 100%;
 display: inline-block;
 vertical-align: bottom;
 border-radius: var(--n-border-radius);
 min-height: var(--n-height);
 line-height: 1.5;
 font-size: var(--n-font-size);
 `,[P(`base-loading`,`
 color: var(--n-loading-color);
 `),P(`base-selection-tags`,`min-height: var(--n-height);`),Y(`border, state-border`,`
 position: absolute;
 left: 0;
 right: 0;
 top: 0;
 bottom: 0;
 pointer-events: none;
 border: var(--n-border);
 border-radius: inherit;
 transition:
 box-shadow .3s var(--n-bezier),
 border-color .3s var(--n-bezier);
 `),Y(`state-border`,`
 z-index: 1;
 border-color: #0000;
 `),P(`base-suffix`,`
 cursor: pointer;
 position: absolute;
 top: 50%;
 transform: translateY(-50%);
 right: 10px;
 `,[Y(`arrow`,`
 font-size: var(--n-arrow-size);
 color: var(--n-arrow-color);
 transition: color .3s var(--n-bezier);
 `)]),P(`base-selection-overlay`,`
 display: flex;
 align-items: center;
 white-space: nowrap;
 pointer-events: none;
 position: absolute;
 top: 0;
 right: 0;
 bottom: 0;
 left: 0;
 padding: var(--n-padding-single);
 transition: color .3s var(--n-bezier);
 `,[Y(`wrapper`,`
 flex-basis: 0;
 flex-grow: 1;
 overflow: hidden;
 text-overflow: ellipsis;
 `)]),P(`base-selection-placeholder`,`
 color: var(--n-placeholder-color);
 `,[Y(`inner`,`
 max-width: 100%;
 overflow: hidden;
 `)]),P(`base-selection-tags`,`
 cursor: pointer;
 outline: none;
 box-sizing: border-box;
 position: relative;
 z-index: auto;
 display: flex;
 padding: var(--n-padding-multiple);
 flex-wrap: wrap;
 align-items: center;
 width: 100%;
 vertical-align: bottom;
 background-color: var(--n-color);
 border-radius: inherit;
 transition:
 color .3s var(--n-bezier),
 box-shadow .3s var(--n-bezier),
 background-color .3s var(--n-bezier);
 `),P(`base-selection-label`,`
 height: var(--n-height);
 display: inline-flex;
 width: 100%;
 vertical-align: bottom;
 cursor: pointer;
 outline: none;
 z-index: auto;
 box-sizing: border-box;
 position: relative;
 transition:
 color .3s var(--n-bezier),
 box-shadow .3s var(--n-bezier),
 background-color .3s var(--n-bezier);
 border-radius: inherit;
 background-color: var(--n-color);
 align-items: center;
 `,[P(`base-selection-input`,`
 font-size: inherit;
 line-height: inherit;
 outline: none;
 cursor: pointer;
 box-sizing: border-box;
 border:none;
 width: 100%;
 padding: var(--n-padding-single);
 background-color: #0000;
 color: var(--n-text-color);
 transition: color .3s var(--n-bezier);
 caret-color: var(--n-caret-color);
 `,[Y(`content`,`
 text-overflow: ellipsis;
 overflow: hidden;
 white-space: nowrap; 
 `)]),Y(`render-label`,`
 color: var(--n-text-color);
 `)]),V(`disabled`,[Z(`&:hover`,[Y(`state-border`,`
 box-shadow: var(--n-box-shadow-hover);
 border: var(--n-border-hover);
 `)]),G(`focus`,[Y(`state-border`,`
 box-shadow: var(--n-box-shadow-focus);
 border: var(--n-border-focus);
 `)]),G(`active`,[Y(`state-border`,`
 box-shadow: var(--n-box-shadow-active);
 border: var(--n-border-active);
 `),P(`base-selection-label`,`background-color: var(--n-color-active);`),P(`base-selection-tags`,`background-color: var(--n-color-active);`)])]),G(`disabled`,`cursor: not-allowed;`,[Y(`arrow`,`
 color: var(--n-arrow-color-disabled);
 `),P(`base-selection-label`,`
 cursor: not-allowed;
 background-color: var(--n-color-disabled);
 `,[P(`base-selection-input`,`
 cursor: not-allowed;
 color: var(--n-text-color-disabled);
 `),Y(`render-label`,`
 color: var(--n-text-color-disabled);
 `)]),P(`base-selection-tags`,`
 cursor: not-allowed;
 background-color: var(--n-color-disabled);
 `),P(`base-selection-placeholder`,`
 cursor: not-allowed;
 color: var(--n-placeholder-color-disabled);
 `)]),P(`base-selection-input-tag`,`
 height: calc(var(--n-height) - 6px);
 line-height: calc(var(--n-height) - 6px);
 outline: none;
 display: none;
 position: relative;
 margin-bottom: 3px;
 max-width: 100%;
 vertical-align: bottom;
 `,[Y(`input`,`
 font-size: inherit;
 font-family: inherit;
 min-width: 1px;
 padding: 0;
 background-color: #0000;
 outline: none;
 border: none;
 max-width: 100%;
 overflow: hidden;
 width: 1em;
 line-height: inherit;
 cursor: pointer;
 color: var(--n-text-color);
 caret-color: var(--n-caret-color);
 `),Y(`mirror`,`
 position: absolute;
 left: 0;
 top: 0;
 white-space: pre;
 visibility: hidden;
 user-select: none;
 -webkit-user-select: none;
 opacity: 0;
 `)]),[`warning`,`error`].map(e=>G(`${e}-status`,[Y(`state-border`,`border: var(--n-border-${e});`),V(`disabled`,[Z(`&:hover`,[Y(`state-border`,`
 box-shadow: var(--n-box-shadow-hover-${e});
 border: var(--n-border-hover-${e});
 `)]),G(`active`,[Y(`state-border`,`
 box-shadow: var(--n-box-shadow-active-${e});
 border: var(--n-border-active-${e});
 `),P(`base-selection-label`,`background-color: var(--n-color-active-${e});`),P(`base-selection-tags`,`background-color: var(--n-color-active-${e});`)]),G(`focus`,[Y(`state-border`,`
 box-shadow: var(--n-box-shadow-focus-${e});
 border: var(--n-border-focus-${e});
 `)])])]))]),P(`base-selection-popover`,`
 margin-bottom: -3px;
 display: flex;
 flex-wrap: wrap;
 margin-right: -8px;
 `),P(`base-selection-tag-wrapper`,`
 max-width: 100%;
 display: inline-flex;
 padding: 0 7px 3px 0;
 `,[Z(`&:last-child`,`padding-right: 0;`),P(`tag`,`
 font-size: 14px;
 max-width: 100%;
 `,[Y(`content`,`
 line-height: 1.25;
 text-overflow: ellipsis;
 overflow: hidden;
 `)])])]),ht=s({name:`InternalSelection`,props:Object.assign(Object.assign({},D.props),{clsPrefix:{type:String,required:!0},bordered:{type:Boolean,default:void 0},active:Boolean,pattern:{type:String,default:``},placeholder:String,selectedOption:{type:Object,default:null},selectedOptions:{type:Array,default:null},labelField:{type:String,default:`label`},valueField:{type:String,default:`value`},multiple:Boolean,filterable:Boolean,clearable:Boolean,disabled:Boolean,size:{type:String,default:`medium`},loading:Boolean,autofocus:Boolean,showArrow:{type:Boolean,default:!0},inputProps:Object,focused:Boolean,renderTag:Function,onKeydown:Function,onClick:Function,onBlur:Function,onFocus:Function,onDeleteOption:Function,maxTagCount:[String,Number],ellipsisTagPopoverProps:Object,onClear:Function,onPatternInput:Function,onPatternFocus:Function,onPatternBlur:Function,renderLabel:Function,status:String,inlineThemeDisabled:Boolean,ignoreComposition:{type:Boolean,default:!0},onResize:Function}),setup(t){let{mergedClsPrefixRef:n,mergedRtlRef:r}=K(t),a=U(`InternalSelection`,r,n),o=e(null),s=e(null),l=e(null),u=e(null),f=e(null),p=e(null),m=e(null),g=e(null),y=e(null),b=e(null),x=e(!1),S=e(!1),C=e(!1),w=D(`InternalSelection`,`-internal-selection`,mt,pt,t,_(t,`clsPrefix`)),T=d(()=>t.clearable&&!t.disabled&&(C.value||t.active)),E=d(()=>t.selectedOption?t.renderTag?t.renderTag({option:t.selectedOption,handleClose:()=>{}}):t.renderLabel?t.renderLabel(t.selectedOption,!0):$(t.selectedOption[t.labelField],t.selectedOption,!0):t.placeholder),O=d(()=>{let e=t.selectedOption;if(e)return e[t.labelField]}),k=d(()=>t.multiple?!!(Array.isArray(t.selectedOptions)&&t.selectedOptions.length):t.selectedOption!==null);function A(){var e;let{value:n}=o;if(n){let{value:r}=s;r&&(r.style.width=`${n.offsetWidth}px`,t.maxTagCount!==`responsive`&&((e=y.value)==null||e.sync({showAllItemsBeforeCalculate:!1})))}}function j(){let{value:e}=b;e&&(e.style.display=`none`)}function M(){let{value:e}=b;e&&(e.style.display=`inline-block`)}i(_(t,`active`),e=>{e||j()}),i(_(t,`pattern`),()=>{t.multiple&&c(A)});function N(e){let{onFocus:n}=t;n&&n(e)}function P(e){let{onBlur:n}=t;n&&n(e)}function F(e){let{onDeleteOption:n}=t;n&&n(e)}function I(e){let{onClear:n}=t;n&&n(e)}function L(e){let{onPatternInput:n}=t;n&&n(e)}function z(e){(!e.relatedTarget||!l.value?.contains(e.relatedTarget))&&N(e)}function B(e){l.value?.contains(e.relatedTarget)||P(e)}function V(e){I(e)}function H(){C.value=!0}function W(){C.value=!1}function ee(e){!t.active||!t.filterable||e.target!==s.value&&e.preventDefault()}function G(e){F(e)}let q=e(!1);function J(e){if(e.key===`Backspace`&&!q.value&&!t.pattern.length){let{selectedOptions:e}=t;e?.length&&G(e[e.length-1])}}let Y=null;function ne(e){let{value:n}=o;n&&(n.textContent=e.target.value,A()),t.ignoreComposition&&q.value?Y=e:L(e)}function Z(){q.value=!0}function re(){q.value=!1,t.ignoreComposition&&L(Y),Y=null}function Q(e){var n;S.value=!0,(n=t.onPatternFocus)==null||n.call(t,e)}function ie(e){var n;S.value=!1,(n=t.onPatternBlur)==null||n.call(t,e)}function ae(){var e,n;if(t.filterable)S.value=!1,(e=p.value)==null||e.blur(),(n=s.value)==null||n.blur();else if(t.multiple){let{value:e}=u;e?.blur()}else{let{value:e}=f;e?.blur()}}function oe(){var e,n,r;t.filterable?(S.value=!1,(e=p.value)==null||e.focus()):t.multiple?(n=u.value)==null||n.focus():(r=f.value)==null||r.focus()}function se(){let{value:e}=s;e&&(M(),e.focus())}function ce(){let{value:e}=s;e&&e.blur()}function le(e){let{value:t}=m;t&&t.setTextContent(`+${e}`)}function ue(){let{value:e}=g;return e}function de(){return s.value}let fe=null;function pe(){fe!==null&&window.clearTimeout(fe)}function me(){t.active||(pe(),fe=window.setTimeout(()=>{k.value&&(x.value=!0)},100))}function he(){pe()}function ge(e){e||(pe(),x.value=!1)}i(k,e=>{e||(x.value=!1)}),v(()=>{h(()=>{let e=p.value;e&&(t.disabled?e.removeAttribute(`tabindex`):e.tabIndex=S.value?-1:0)})}),ze(l,t.onResize);let{inlineThemeDisabled:_e}=t,ve=d(()=>{let{size:e}=t,{common:{cubicBezierEaseInOut:n},self:{fontWeight:r,borderRadius:i,color:a,placeholderColor:o,textColor:s,paddingSingle:c,paddingMultiple:l,caretColor:u,colorDisabled:d,textColorDisabled:f,placeholderColorDisabled:p,colorActive:m,boxShadowFocus:h,boxShadowActive:g,boxShadowHover:_,border:v,borderFocus:y,borderHover:b,borderActive:x,arrowColor:S,arrowColorDisabled:C,loadingColor:T,colorActiveWarning:E,boxShadowFocusWarning:D,boxShadowActiveWarning:O,boxShadowHoverWarning:k,borderWarning:A,borderFocusWarning:j,borderHoverWarning:M,borderActiveWarning:N,colorActiveError:P,boxShadowFocusError:F,boxShadowActiveError:I,boxShadowHoverError:L,borderError:z,borderFocusError:B,borderHoverError:V,borderActiveError:H,clearColor:U,clearColorHover:W,clearColorPressed:ee,clearSize:G,arrowSize:K,[R(`height`,e)]:q,[R(`fontSize`,e)]:J}}=w.value,Y=te(c),X=te(l);return{"--n-bezier":n,"--n-border":v,"--n-border-active":x,"--n-border-focus":y,"--n-border-hover":b,"--n-border-radius":i,"--n-box-shadow-active":g,"--n-box-shadow-focus":h,"--n-box-shadow-hover":_,"--n-caret-color":u,"--n-color":a,"--n-color-active":m,"--n-color-disabled":d,"--n-font-size":J,"--n-height":q,"--n-padding-single-top":Y.top,"--n-padding-multiple-top":X.top,"--n-padding-single-right":Y.right,"--n-padding-multiple-right":X.right,"--n-padding-single-left":Y.left,"--n-padding-multiple-left":X.left,"--n-padding-single-bottom":Y.bottom,"--n-padding-multiple-bottom":X.bottom,"--n-placeholder-color":o,"--n-placeholder-color-disabled":p,"--n-text-color":s,"--n-text-color-disabled":f,"--n-arrow-color":S,"--n-arrow-color-disabled":C,"--n-loading-color":T,"--n-color-active-warning":E,"--n-box-shadow-focus-warning":D,"--n-box-shadow-active-warning":O,"--n-box-shadow-hover-warning":k,"--n-border-warning":A,"--n-border-focus-warning":j,"--n-border-hover-warning":M,"--n-border-active-warning":N,"--n-color-active-error":P,"--n-box-shadow-focus-error":F,"--n-box-shadow-active-error":I,"--n-box-shadow-hover-error":L,"--n-border-error":z,"--n-border-focus-error":B,"--n-border-hover-error":V,"--n-border-active-error":H,"--n-clear-size":G,"--n-clear-color":U,"--n-clear-color-hover":W,"--n-clear-color-pressed":ee,"--n-arrow-size":K,"--n-font-weight":r}}),ye=_e?X(`internal-selection`,d(()=>t.size[0]),ve,t):void 0;return{mergedTheme:w,mergedClearable:T,mergedClsPrefix:n,rtlEnabled:a,patternInputFocused:S,filterablePlaceholder:E,label:O,selected:k,showTagsPanel:x,isComposing:q,counterRef:m,counterWrapperRef:g,patternInputMirrorRef:o,patternInputRef:s,selfRef:l,multipleElRef:u,singleElRef:f,patternInputWrapperRef:p,overflowRef:y,inputTagElRef:b,handleMouseDown:ee,handleFocusin:z,handleClear:V,handleMouseEnter:H,handleMouseLeave:W,handleDeleteOption:G,handlePatternKeyDown:J,handlePatternInputInput:ne,handlePatternInputBlur:ie,handlePatternInputFocus:Q,handleMouseEnterCounter:me,handleMouseLeaveCounter:he,handleFocusout:B,handleCompositionEnd:re,handleCompositionStart:Z,onPopoverUpdateShow:ge,focus:oe,focusInput:se,blur:ae,blurInput:ce,updateCounter:le,getCounter:ue,getTail:de,renderLabel:t.renderLabel,cssVars:_e?void 0:ve,themeClass:ye?.themeClass,onRender:ye?.onRender}},render(){let{status:e,multiple:n,size:r,disabled:i,filterable:a,maxTagCount:o,bordered:s,clsPrefix:c,ellipsisTagPopoverProps:l,onRender:u,renderTag:d,renderLabel:f}=this;u?.();let m=o===`responsive`,h=typeof o==`number`,g=m||h,_=t(z,null,{default:()=>t(Ee,{clsPrefix:c,loading:this.loading,showArrow:this.showArrow,showClear:this.mergedClearable&&this.selected,onClear:this.handleClear},{default:()=>{var e;return(e=this.$slots).arrow?.call(e)}})}),v;if(n){let{labelField:e}=this,n=n=>t(`div`,{class:`${c}-base-selection-tag-wrapper`,key:n.value},d?d({option:n,handleClose:()=>{this.handleDeleteOption(n)}}):t(xe,{size:r,closable:!n.disabled,disabled:i,onClose:()=>{this.handleDeleteOption(n)},internalCloseIsButtonTag:!1,internalCloseFocusable:!1},{default:()=>f?f(n,!0):$(n[e],n,!0)})),s=()=>(h?this.selectedOptions.slice(0,o):this.selectedOptions).map(n),u=a?t(`div`,{class:`${c}-base-selection-input-tag`,ref:`inputTagElRef`,key:`__input-tag__`},t(`input`,Object.assign({},this.inputProps,{ref:`patternInputRef`,tabindex:-1,disabled:i,value:this.pattern,autofocus:this.autofocus,class:`${c}-base-selection-input-tag__input`,onBlur:this.handlePatternInputBlur,onFocus:this.handlePatternInputFocus,onKeydown:this.handlePatternKeyDown,onInput:this.handlePatternInputInput,onCompositionstart:this.handleCompositionStart,onCompositionend:this.handleCompositionEnd})),t(`span`,{ref:`patternInputMirrorRef`,class:`${c}-base-selection-input-tag__mirror`},this.pattern)):null,y=m?()=>t(`div`,{class:`${c}-base-selection-tag-wrapper`,ref:`counterWrapperRef`},t(xe,{size:r,ref:`counterRef`,onMouseenter:this.handleMouseEnterCounter,onMouseleave:this.handleMouseLeaveCounter,disabled:i})):void 0,b;if(h){let e=this.selectedOptions.length-o;e>0&&(b=t(`div`,{class:`${c}-base-selection-tag-wrapper`,key:`__counter__`},t(xe,{size:r,ref:`counterRef`,onMouseenter:this.handleMouseEnterCounter,disabled:i},{default:()=>`+${e}`})))}let x=m?a?t(ve,{ref:`overflowRef`,updateCounter:this.updateCounter,getCounter:this.getCounter,getTail:this.getTail,style:{width:`100%`,display:`flex`,overflow:`hidden`}},{default:s,counter:y,tail:()=>u}):t(ve,{ref:`overflowRef`,updateCounter:this.updateCounter,getCounter:this.getCounter,style:{width:`100%`,display:`flex`,overflow:`hidden`}},{default:s,counter:y}):h&&b?s().concat(b):s(),S=g?()=>t(`div`,{class:`${c}-base-selection-popover`},m?s():this.selectedOptions.map(n)):void 0,C=g?Object.assign({show:this.showTagsPanel,trigger:`hover`,overlap:!0,placement:`top`,width:`trigger`,onUpdateShow:this.onPopoverUpdateShow,theme:this.mergedTheme.peers.Popover,themeOverrides:this.mergedTheme.peerOverrides.Popover},l):null,w=!this.selected&&(!this.active||!this.pattern&&!this.isComposing)?t(`div`,{class:`${c}-base-selection-placeholder ${c}-base-selection-overlay`},t(`div`,{class:`${c}-base-selection-placeholder__inner`},this.placeholder)):null,T=a?t(`div`,{ref:`patternInputWrapperRef`,class:`${c}-base-selection-tags`},x,m?null:u,_):t(`div`,{ref:`multipleElRef`,class:`${c}-base-selection-tags`,tabindex:i?void 0:0},x,_);v=t(p,null,g?t(me,Object.assign({},C,{scrollable:!0,style:`max-height: calc(var(--v-target-height) * 6.6);`}),{trigger:()=>T,default:S}):T,w)}else if(a){let e=this.pattern||this.isComposing,n=this.active?!e:!this.selected,r=this.active?!1:this.selected;v=t(`div`,{ref:`patternInputWrapperRef`,class:`${c}-base-selection-label`,title:this.patternInputFocused?void 0:Be(this.label)},t(`input`,Object.assign({},this.inputProps,{ref:`patternInputRef`,class:`${c}-base-selection-input`,value:this.active?this.pattern:``,placeholder:``,readonly:i,disabled:i,tabindex:-1,autofocus:this.autofocus,onFocus:this.handlePatternInputFocus,onBlur:this.handlePatternInputBlur,onInput:this.handlePatternInputInput,onCompositionstart:this.handleCompositionStart,onCompositionend:this.handleCompositionEnd})),r?t(`div`,{class:`${c}-base-selection-label__render-label ${c}-base-selection-overlay`,key:`input`},t(`div`,{class:`${c}-base-selection-overlay__wrapper`},d?d({option:this.selectedOption,handleClose:()=>{}}):f?f(this.selectedOption,!0):$(this.label,this.selectedOption,!0))):null,n?t(`div`,{class:`${c}-base-selection-placeholder ${c}-base-selection-overlay`,key:`placeholder`},t(`div`,{class:`${c}-base-selection-overlay__wrapper`},this.filterablePlaceholder)):null,_)}else v=t(`div`,{ref:`singleElRef`,class:`${c}-base-selection-label`,tabindex:this.disabled?void 0:0},this.label===void 0?t(`div`,{class:`${c}-base-selection-placeholder ${c}-base-selection-overlay`,key:`placeholder`},t(`div`,{class:`${c}-base-selection-placeholder__inner`},this.placeholder)):t(`div`,{class:`${c}-base-selection-input`,title:Be(this.label),key:`input`},t(`div`,{class:`${c}-base-selection-input__content`},d?d({option:this.selectedOption,handleClose:()=>{}}):f?f(this.selectedOption,!0):$(this.label,this.selectedOption,!0))),_);return t(`div`,{ref:`selfRef`,class:[`${c}-base-selection`,this.rtlEnabled&&`${c}-base-selection--rtl`,this.themeClass,e&&`${c}-base-selection--${e}-status`,{[`${c}-base-selection--active`]:this.active,[`${c}-base-selection--selected`]:this.selected||this.active&&this.pattern,[`${c}-base-selection--disabled`]:this.disabled,[`${c}-base-selection--multiple`]:this.multiple,[`${c}-base-selection--focus`]:this.focused}],style:this.cssVars,onClick:this.onClick,onMouseenter:this.handleMouseEnter,onMouseleave:this.handleMouseLeave,onKeydown:this.onKeydown,onFocusin:this.handleFocusin,onFocusout:this.handleFocusout,onMousedown:this.handleMouseDown},v,s?t(`div`,{class:`${c}-base-selection__border`}):null,s?t(`div`,{class:`${c}-base-selection__state-border`}):null)}});function gt(e){return e.type===`group`}function _t(e){return e.type===`ignored`}function vt(e,t){try{return!!(1+t.toString().toLowerCase().indexOf(e.trim().toLowerCase()))}catch{return!1}}function yt(e,t){return{getIsGroup:gt,getIgnored:_t,getKey(t){return gt(t)?t.name||t.key||`key-required`:t[e]},getChildren(e){return e[t]}}}function bt(e,t,n,r){if(!t)return e;function i(e){if(!Array.isArray(e))return[];let a=[];for(let o of e)if(gt(o)){let e=i(o[r]);e.length&&a.push(Object.assign({},o,{[r]:e}))}else if(_t(o))continue;else t(n,o)&&a.push(o);return a}return i(e)}function xt(e,t,n){let r=new Map;return e.forEach(e=>{gt(e)?e[n].forEach(e=>{r.set(e[t],e)}):r.set(e[t],e)}),r}function St(e){let{boxShadow2:t}=e;return{menuBoxShadow:t}}var Ct=x({name:`Popselect`,common:J,peers:{Popover:ce,InternalSelectMenu:at},self:St}),wt=A(`n-popselect`),Tt=P(`popselect-menu`,`
 box-shadow: var(--n-menu-box-shadow);
`),Et={multiple:Boolean,value:{type:[String,Number,Array],default:null},cancelable:Boolean,options:{type:Array,default:()=>[]},size:String,scrollable:Boolean,"onUpdate:value":[Function,Array],onUpdateValue:[Function,Array],onMouseenter:Function,onMouseleave:Function,renderLabel:Function,showCheckmark:{type:Boolean,default:void 0},nodeProps:Function,virtualScroll:Boolean,onChange:[Function,Array]},Dt=b(Et),Ot=s({name:`PopselectPanel`,props:Et,setup(e){let t=m(wt),{mergedClsPrefixRef:n,inlineThemeDisabled:r,mergedComponentPropsRef:a}=K(e),o=d(()=>e.size||a?.value?.Popselect?.size||`medium`),s=D(`Popselect`,`-pop-select`,Tt,Ct,t.props,n),l=d(()=>ye(e.options,yt(`value`,`children`)));function u(t,n){let{onUpdateValue:r,"onUpdate:value":i,onChange:a}=e;r&&S(r,t,n),i&&S(i,t,n),a&&S(a,t,n)}function f(e){h(e.key)}function p(e){!be(e,`action`)&&!be(e,`empty`)&&!be(e,`header`)&&e.preventDefault()}function h(n){let{value:{getNode:r}}=l;if(e.multiple)if(Array.isArray(e.value)){let t=[],i=[],a=!0;e.value.forEach(e=>{if(e===n){a=!1;return}let o=r(e);o&&(t.push(o.key),i.push(o.rawNode))}),a&&(t.push(n),i.push(r(n).rawNode)),u(t,i)}else{let e=r(n);e&&u([n],[e.rawNode])}else if(e.value===n&&e.cancelable)u(null,null);else{let e=r(n);e&&u(n,e.rawNode);let{"onUpdate:show":i,onUpdateShow:a}=t.props;i&&S(i,!1),a&&S(a,!1),t.setShow(!1)}c(()=>{t.syncPosition()})}i(_(e,`options`),()=>{c(()=>{t.syncPosition()})});let g=d(()=>{let{self:{menuBoxShadow:e}}=s.value;return{"--n-menu-box-shadow":e}}),v=r?X(`select`,void 0,g,t.props):void 0;return{mergedTheme:t.mergedThemeRef,mergedClsPrefix:n,treeMate:l,handleToggle:f,handleMenuMousedown:p,cssVars:r?void 0:g,themeClass:v?.themeClass,onRender:v?.onRender,mergedSize:o,scrollbarProps:t.props.scrollbarProps}},render(){var e;return(e=this.onRender)==null||e.call(this),t(ut,{clsPrefix:this.mergedClsPrefix,focusable:!0,nodeProps:this.nodeProps,class:[`${this.mergedClsPrefix}-popselect-menu`,this.themeClass],style:this.cssVars,theme:this.mergedTheme.peers.InternalSelectMenu,themeOverrides:this.mergedTheme.peerOverrides.InternalSelectMenu,multiple:this.multiple,treeMate:this.treeMate,size:this.mergedSize,value:this.value,virtualScroll:this.virtualScroll,scrollable:this.scrollable,scrollbarProps:this.scrollbarProps,renderLabel:this.renderLabel,onToggle:this.handleToggle,onMouseenter:this.onMouseenter,onMouseleave:this.onMouseenter,onMousedown:this.handleMenuMousedown,showCheckmark:this.showCheckmark},{header:()=>{var e;return(e=this.$slots).header?.call(e)||[]},action:()=>{var e;return(e=this.$slots).action?.call(e)||[]},empty:()=>{var e;return(e=this.$slots).empty?.call(e)||[]}})}}),kt=s({name:`Popselect`,props:Object.assign(Object.assign(Object.assign(Object.assign(Object.assign({},D.props),k(de,[`showArrow`,`arrow`])),{placement:Object.assign(Object.assign({},de.placement),{default:`bottom`}),trigger:{type:String,default:`hover`}}),Et),{scrollbarProps:Object}),slots:Object,inheritAttrs:!1,__popover__:!0,setup(t){let{mergedClsPrefixRef:n}=K(t),i=D(`Popselect`,`-popselect`,void 0,Ct,t,n),a=e(null);function o(){var e;(e=a.value)==null||e.syncPosition()}function s(e){var t;(t=a.value)==null||t.setShow(e)}return r(wt,{props:t,mergedThemeRef:i,syncPosition:o,setShow:s}),Object.assign(Object.assign({},{syncPosition:o,setShow:s}),{popoverInstRef:a,mergedTheme:i})},render(){let{mergedTheme:e}=this,n={theme:e.peers.Popover,themeOverrides:e.peerOverrides.Popover,builtinThemeOverrides:{padding:`0`},ref:`popoverInstRef`,internalRenderBody:(e,n,r,i,a)=>{let{$attrs:o}=this;return t(Ot,Object.assign({},o,{class:[o.class,e],style:[o.style,...r]},Q(this.$props,Dt),{ref:ge(n),onMouseenter:Ue([i,o.onMouseenter]),onMouseleave:Ue([a,o.onMouseleave])}),{header:()=>{var e;return(e=this.$slots).header?.call(e)},action:()=>{var e;return(e=this.$slots).action?.call(e)},empty:()=>{var e;return(e=this.$slots).empty?.call(e)}})}};return t(me,Object.assign({},k(this.$props,Dt),n,{internalDeactivateImmediately:!0}),{trigger:()=>{var e;return(e=this.$slots).default?.call(e)}})}});function At(e){let{boxShadow2:t}=e;return{menuBoxShadow:t}}var jt=x({name:`Select`,common:J,peers:{InternalSelection:pt,InternalSelectMenu:at},self:At}),Mt=Z([P(`select`,`
 z-index: auto;
 outline: none;
 width: 100%;
 position: relative;
 font-weight: var(--n-font-weight);
 `),P(`select-menu`,`
 margin: 4px 0;
 box-shadow: var(--n-menu-box-shadow);
 `,[W({originalTransition:`background-color .3s var(--n-bezier), box-shadow .3s var(--n-bezier)`})])]),Nt=s({name:`Select`,props:Object.assign(Object.assign({},D.props),{to:oe.propTo,bordered:{type:Boolean,default:void 0},clearable:Boolean,clearCreatedOptionsOnClear:{type:Boolean,default:!0},clearFilterAfterSelect:{type:Boolean,default:!0},options:{type:Array,default:()=>[]},defaultValue:{type:[String,Number,Array],default:null},keyboard:{type:Boolean,default:!0},value:[String,Number,Array],placeholder:String,menuProps:Object,multiple:Boolean,size:String,menuSize:{type:String},filterable:Boolean,disabled:{type:Boolean,default:void 0},remote:Boolean,loading:Boolean,filter:Function,placement:{type:String,default:`bottom-start`},widthMode:{type:String,default:`trigger`},tag:Boolean,onCreate:Function,fallbackOption:{type:[Function,Boolean],default:void 0},show:{type:Boolean,default:void 0},showArrow:{type:Boolean,default:!0},maxTagCount:[Number,String],ellipsisTagPopoverProps:Object,consistentMenuWidth:{type:Boolean,default:!0},virtualScroll:{type:Boolean,default:!0},labelField:{type:String,default:`label`},valueField:{type:String,default:`value`},childrenField:{type:String,default:`children`},renderLabel:Function,renderOption:Function,renderTag:Function,"onUpdate:value":[Function,Array],inputProps:Object,nodeProps:Function,ignoreComposition:{type:Boolean,default:!0},showOnFocus:Boolean,onUpdateValue:[Function,Array],onBlur:[Function,Array],onClear:[Function,Array],onFocus:[Function,Array],onScroll:[Function,Array],onSearch:[Function,Array],onUpdateShow:[Function,Array],"onUpdate:show":[Function,Array],displayDirective:{type:String,default:`show`},resetMenuOnOptionsChange:{type:Boolean,default:!0},status:String,showCheckmark:{type:Boolean,default:!0},scrollbarProps:Object,onChange:[Function,Array],items:Array}),slots:Object,setup(t){let{mergedClsPrefixRef:n,mergedBorderedRef:r,namespaceRef:a,inlineThemeDisabled:o,mergedComponentPropsRef:s}=K(t),c=D(`Select`,`-select`,Mt,jt,t,n),l=e(t.defaultValue),u=Se(_(t,`value`),l),f=e(!1),p=e(``),m=Ce(t,[`items`,`options`]),h=e([]),g=e([]),v=d(()=>g.value.concat(h.value).concat(m.value)),y=d(()=>{let{filter:e}=t;if(e)return e;let{labelField:n,valueField:r}=t;return(e,t)=>{if(!t)return!1;let i=t[n];if(typeof i==`string`)return vt(e,i);let a=t[r];return typeof a==`string`?vt(e,a):typeof a==`number`?vt(e,String(a)):!1}}),b=d(()=>{if(t.remote)return m.value;{let{value:e}=v,{value:n}=p;return!n.length||!t.filterable?e:bt(e,y.value,n,t.childrenField)}}),x=d(()=>{let{valueField:e,childrenField:n}=t,r=yt(e,n);return ye(b.value,r)}),C=d(()=>xt(v.value,t.valueField,t.childrenField)),w=e(!1),T=Se(_(t,`show`),w),O=e(null),k=e(null),A=e(null),{localeRef:M}=we(`Select`),N=d(()=>t.placeholder??M.value.placeholder),P=[],F=e(new Map),I=d(()=>{let{fallbackOption:e}=t;if(e===void 0){let{labelField:e,valueField:n}=t;return t=>({[e]:String(t),[n]:t})}return e===!1?!1:t=>Object.assign(e(t),{value:t})});function R(e){let n=t.remote,{value:r}=F,{value:i}=C,{value:a}=I,o=[];return e.forEach(e=>{if(i.has(e))o.push(i.get(e));else if(n&&r.has(e))o.push(r.get(e));else if(a){let t=a(e);t&&o.push(t)}}),o}let z=d(()=>{if(t.multiple){let{value:e}=u;return Array.isArray(e)?R(e):[]}return null}),B=d(()=>{let{value:e}=u;return!t.multiple&&!Array.isArray(e)?e===null?null:R([e])[0]||null:null}),V=L(t,{mergedSize:e=>{let{size:n}=t;if(n)return n;let{mergedSize:r}=e||{};return r?.value?r.value:s?.value?.Select?.size||`medium`}}),{mergedSizeRef:H,mergedDisabledRef:U,mergedStatusRef:W}=V;function G(e,n){let{onChange:r,"onUpdate:value":i,onUpdateValue:a}=t,{nTriggerFormChange:o,nTriggerFormInput:s}=V;r&&S(r,e,n),a&&S(a,e,n),i&&S(i,e,n),l.value=e,o(),s()}function q(e){let{onBlur:n}=t,{nTriggerFormBlur:r}=V;n&&S(n,e),r()}function J(){let{onClear:e}=t;e&&S(e)}function Y(e){let{onFocus:n,showOnFocus:r}=t,{nTriggerFormFocus:i}=V;n&&S(n,e),i(),r&&Q()}function te(e){let{onSearch:n}=t;n&&S(n,e)}function ne(e){let{onScroll:n}=t;n&&S(n,e)}function Z(){var e;let{remote:n,multiple:r}=t;if(n){let{value:n}=F;if(r){let{valueField:r}=t;(e=z.value)==null||e.forEach(e=>{n.set(e[r],e)})}else{let e=B.value;e&&n.set(e[t.valueField],e)}}}function re(e){let{onUpdateShow:n,"onUpdate:show":r}=t;n&&S(n,e),r&&S(r,e),w.value=e}function Q(){U.value||(re(!0),w.value=!0,t.filterable&&je())}function $(){re(!1)}function ie(){p.value=``,g.value=P}let ae=e(!1);function se(){t.filterable&&(ae.value=!0)}function ce(){t.filterable&&(ae.value=!1,T.value||ie())}function le(){U.value||(T.value?t.filterable?je():$():Q())}function ue(e){(A.value?.selfRef)?.contains(e.relatedTarget)||(f.value=!1,q(e),$())}function de(e){Y(e),f.value=!0}function fe(){f.value=!0}function pe(e){O.value?.$el.contains(e.relatedTarget)||(f.value=!1,q(e),$())}function me(){var e;(e=O.value)==null||e.focus(),$()}function he(e){T.value&&(O.value?.$el.contains(ee(e))||$())}function ge(e){if(!Array.isArray(e))return[];if(I.value)return Array.from(e);{let{remote:n}=t,{value:r}=C;if(n){let{value:t}=F;return e.filter(e=>r.has(e)||t.has(e))}else return e.filter(e=>r.has(e))}}function _e(e){ve(e.rawNode)}function ve(e){if(U.value)return;let{tag:n,remote:r,clearFilterAfterSelect:i,valueField:a}=t;if(n&&!r){let{value:e}=g,t=e[0]||null;if(t){let e=h.value;e.length?e.push(t):h.value=[t],g.value=P}}if(r&&F.value.set(e[a],e),t.multiple){let t=ge(u.value),o=t.findIndex(t=>t===e[a]);if(~o){if(t.splice(o,1),n&&!r){let t=xe(e[a]);~t&&(h.value.splice(t,1),i&&(p.value=``))}}else t.push(e[a]),i&&(p.value=``);G(t,R(t))}else{if(n&&!r){let t=xe(e[a]);~t?h.value=[h.value[t]]:h.value=P}Ae(),$(),G(e[a],e)}}function xe(e){return h.value.findIndex(n=>n[t.valueField]===e)}function Te(e){T.value||Q();let{value:n}=e.target;p.value=n;let{tag:r,remote:i}=t;if(te(n),r&&!i){if(!n){g.value=P;return}let{onCreate:e}=t,r=e?e(n):{[t.labelField]:n,[t.valueField]:n},{valueField:i,labelField:a}=t;m.value.some(e=>e[i]===r[i]||e[a]===r[a])||h.value.some(e=>e[i]===r[i]||e[a]===r[a])?g.value=P:g.value=[r]}}function Ee(e){e.stopPropagation();let{multiple:n,tag:r,remote:i,clearCreatedOptionsOnClear:a}=t;!n&&t.filterable&&$(),r&&!i&&a&&(h.value=P),J(),n?G([],[]):G(null,null)}function De(e){!be(e,`action`)&&!be(e,`empty`)&&!be(e,`header`)&&e.preventDefault()}function Oe(e){ne(e)}function ke(e){var n,r,i;if(!t.keyboard){e.preventDefault();return}switch(e.key){case` `:if(t.filterable)break;e.preventDefault();case`Enter`:if(!O.value?.isComposing){if(T.value){let e=A.value?.getPendingTmNode();e?_e(e):t.filterable||($(),Ae())}else if(Q(),t.tag&&ae.value){let e=g.value[0];if(e){let n=e[t.valueField],{value:r}=u;t.multiple&&Array.isArray(r)&&r.includes(n)||ve(e)}}}e.preventDefault();break;case`ArrowUp`:if(e.preventDefault(),t.loading)return;T.value&&((n=A.value)==null||n.prev());break;case`ArrowDown`:if(e.preventDefault(),t.loading)return;T.value?(r=A.value)==null||r.next():Q();break;case`Escape`:T.value&&(E(e),$()),(i=O.value)==null||i.focus();break}}function Ae(){var e;(e=O.value)==null||e.focus()}function je(){var e;(e=O.value)==null||e.focusInput()}function Me(){var e;T.value&&((e=k.value)==null||e.syncPosition())}Z(),i(_(t,`options`),Z);let Ne={focus:()=>{var e;(e=O.value)==null||e.focus()},focusInput:()=>{var e;(e=O.value)==null||e.focusInput()},blur:()=>{var e;(e=O.value)==null||e.blur()},blurInput:()=>{var e;(e=O.value)==null||e.blurInput()}},Pe=d(()=>{let{self:{menuBoxShadow:e}}=c.value;return{"--n-menu-box-shadow":e}}),Fe=o?X(`select`,void 0,Pe,t):void 0;return Object.assign(Object.assign({},Ne),{mergedStatus:W,mergedClsPrefix:n,mergedBordered:r,namespace:a,treeMate:x,isMounted:j(),triggerRef:O,menuRef:A,pattern:p,uncontrolledShow:w,mergedShow:T,adjustedTo:oe(t),uncontrolledValue:l,mergedValue:u,followerRef:k,localizedPlaceholder:N,selectedOption:B,selectedOptions:z,mergedSize:H,mergedDisabled:U,focused:f,activeWithoutMenuOpen:ae,inlineThemeDisabled:o,onTriggerInputFocus:se,onTriggerInputBlur:ce,handleTriggerOrMenuResize:Me,handleMenuFocus:fe,handleMenuBlur:pe,handleMenuTabOut:me,handleTriggerClick:le,handleToggle:_e,handleDeleteOption:ve,handlePatternInput:Te,handleClear:Ee,handleTriggerBlur:ue,handleTriggerFocus:de,handleKeydown:ke,handleMenuAfterLeave:ie,handleMenuClickOutside:he,handleMenuScroll:Oe,handleMenuKeydown:ke,handleMenuMousedown:De,mergedTheme:c,cssVars:o?void 0:Pe,themeClass:Fe?.themeClass,onRender:Fe?.onRender})},render(){return t(`div`,{class:`${this.mergedClsPrefix}-select`},t(ae,null,{default:()=>[t(he,null,{default:()=>t(ht,{ref:`triggerRef`,inlineThemeDisabled:this.inlineThemeDisabled,status:this.mergedStatus,inputProps:this.inputProps,clsPrefix:this.mergedClsPrefix,showArrow:this.showArrow,maxTagCount:this.maxTagCount,ellipsisTagPopoverProps:this.ellipsisTagPopoverProps,bordered:this.mergedBordered,active:this.activeWithoutMenuOpen||this.mergedShow,pattern:this.pattern,placeholder:this.localizedPlaceholder,selectedOption:this.selectedOption,selectedOptions:this.selectedOptions,multiple:this.multiple,renderTag:this.renderTag,renderLabel:this.renderLabel,filterable:this.filterable,clearable:this.clearable,disabled:this.mergedDisabled,size:this.mergedSize,theme:this.mergedTheme.peers.InternalSelection,labelField:this.labelField,valueField:this.valueField,themeOverrides:this.mergedTheme.peerOverrides.InternalSelection,loading:this.loading,focused:this.focused,onClick:this.handleTriggerClick,onDeleteOption:this.handleDeleteOption,onPatternInput:this.handlePatternInput,onClear:this.handleClear,onBlur:this.handleTriggerBlur,onFocus:this.handleTriggerFocus,onKeydown:this.handleKeydown,onPatternBlur:this.onTriggerInputBlur,onPatternFocus:this.onTriggerInputFocus,onResize:this.handleTriggerOrMenuResize,ignoreComposition:this.ignoreComposition},{arrow:()=>{var e;return[(e=this.$slots).arrow?.call(e)]}})}),t(pe,{ref:`followerRef`,show:this.mergedShow,to:this.adjustedTo,teleportDisabled:this.adjustedTo===oe.tdkey,containerClass:this.namespace,width:this.consistentMenuWidth?`target`:void 0,minWidth:`target`,placement:this.placement},{default:()=>t(g,{name:`fade-in-scale-up-transition`,appear:this.isMounted,onAfterLeave:this.handleMenuAfterLeave},{default:()=>{var e;return this.mergedShow||this.displayDirective===`show`?((e=this.onRender)==null||e.call(this),u(t(ut,Object.assign({},this.menuProps,{ref:`menuRef`,onResize:this.handleTriggerOrMenuResize,inlineThemeDisabled:this.inlineThemeDisabled,virtualScroll:this.consistentMenuWidth&&this.virtualScroll,class:[`${this.mergedClsPrefix}-select-menu`,this.themeClass,this.menuProps?.class],clsPrefix:this.mergedClsPrefix,focusable:!0,labelField:this.labelField,valueField:this.valueField,autoPending:!0,nodeProps:this.nodeProps,theme:this.mergedTheme.peers.InternalSelectMenu,themeOverrides:this.mergedTheme.peerOverrides.InternalSelectMenu,treeMate:this.treeMate,multiple:this.multiple,size:this.menuSize,renderOption:this.renderOption,renderLabel:this.renderLabel,value:this.mergedValue,style:[this.menuProps?.style,this.cssVars],onToggle:this.handleToggle,onScroll:this.handleMenuScroll,onFocus:this.handleMenuFocus,onBlur:this.handleMenuBlur,onKeydown:this.handleMenuKeydown,onTabOut:this.handleMenuTabOut,onMousedown:this.handleMenuMousedown,show:this.mergedShow,showCheckmark:this.showCheckmark,resetMenuOnOptionsChange:this.resetMenuOnOptionsChange,scrollbarProps:this.scrollbarProps}),{empty:()=>{var e;return[(e=this.$slots).empty?.call(e)]},header:()=>{var e;return[(e=this.$slots).header?.call(e)]},action:()=>{var e;return[(e=this.$slots).action?.call(e)]}}),this.displayDirective===`show`?[[f,this.mergedShow],[y,this.handleMenuClickOutside,void 0,{capture:!0}]]:[[y,this.handleMenuClickOutside,void 0,{capture:!0}]])):null}})})]}))}}),Pt={itemPaddingSmall:`0 4px`,itemMarginSmall:`0 0 0 8px`,itemMarginSmallRtl:`0 8px 0 0`,itemPaddingMedium:`0 4px`,itemMarginMedium:`0 0 0 8px`,itemMarginMediumRtl:`0 8px 0 0`,itemPaddingLarge:`0 4px`,itemMarginLarge:`0 0 0 8px`,itemMarginLargeRtl:`0 8px 0 0`,buttonIconSizeSmall:`14px`,buttonIconSizeMedium:`16px`,buttonIconSizeLarge:`18px`,inputWidthSmall:`60px`,selectWidthSmall:`unset`,inputMarginSmall:`0 0 0 8px`,inputMarginSmallRtl:`0 8px 0 0`,selectMarginSmall:`0 0 0 8px`,prefixMarginSmall:`0 8px 0 0`,suffixMarginSmall:`0 0 0 8px`,inputWidthMedium:`60px`,selectWidthMedium:`unset`,inputMarginMedium:`0 0 0 8px`,inputMarginMediumRtl:`0 8px 0 0`,selectMarginMedium:`0 0 0 8px`,prefixMarginMedium:`0 8px 0 0`,suffixMarginMedium:`0 0 0 8px`,inputWidthLarge:`60px`,selectWidthLarge:`unset`,inputMarginLarge:`0 0 0 8px`,inputMarginLargeRtl:`0 8px 0 0`,selectMarginLarge:`0 0 0 8px`,prefixMarginLarge:`0 8px 0 0`,suffixMarginLarge:`0 0 0 8px`};function Ft(e){let{textColor2:t,primaryColor:n,primaryColorHover:r,primaryColorPressed:i,inputColorDisabled:a,textColorDisabled:o,borderColor:s,borderRadius:c,fontSizeTiny:l,fontSizeSmall:u,fontSizeMedium:d,heightTiny:f,heightSmall:p,heightMedium:m}=e;return Object.assign(Object.assign({},Pt),{buttonColor:`#0000`,buttonColorHover:`#0000`,buttonColorPressed:`#0000`,buttonBorder:`1px solid ${s}`,buttonBorderHover:`1px solid ${s}`,buttonBorderPressed:`1px solid ${s}`,buttonIconColor:t,buttonIconColorHover:t,buttonIconColorPressed:t,itemTextColor:t,itemTextColorHover:r,itemTextColorPressed:i,itemTextColorActive:n,itemTextColorDisabled:o,itemColor:`#0000`,itemColorHover:`#0000`,itemColorPressed:`#0000`,itemColorActive:`#0000`,itemColorActiveHover:`#0000`,itemColorDisabled:a,itemBorder:`1px solid #0000`,itemBorderHover:`1px solid #0000`,itemBorderPressed:`1px solid #0000`,itemBorderActive:`1px solid ${n}`,itemBorderDisabled:`1px solid ${s}`,itemBorderRadius:c,itemSizeSmall:f,itemSizeMedium:p,itemSizeLarge:m,itemFontSizeSmall:l,itemFontSizeMedium:u,itemFontSizeLarge:d,jumperFontSizeSmall:l,jumperFontSizeMedium:u,jumperFontSizeLarge:d,jumperTextColor:t,jumperTextColorDisabled:o})}var It=x({name:`Pagination`,common:J,peers:{Select:jt,Input:Te,Popselect:Ct},self:Ft}),Lt=`
 background: var(--n-item-color-hover);
 color: var(--n-item-text-color-hover);
 border: var(--n-item-border-hover);
`,Rt=[G(`button`,`
 background: var(--n-button-color-hover);
 border: var(--n-button-border-hover);
 color: var(--n-button-icon-color-hover);
 `)],zt=P(`pagination`,`
 display: flex;
 vertical-align: middle;
 font-size: var(--n-item-font-size);
 flex-wrap: nowrap;
`,[P(`pagination-prefix`,`
 display: flex;
 align-items: center;
 margin: var(--n-prefix-margin);
 `),P(`pagination-suffix`,`
 display: flex;
 align-items: center;
 margin: var(--n-suffix-margin);
 `),Z(`> *:not(:first-child)`,`
 margin: var(--n-item-margin);
 `),P(`select`,`
 width: var(--n-select-width);
 `),Z(`&.transition-disabled`,[P(`pagination-item`,`transition: none!important;`)]),P(`pagination-quick-jumper`,`
 white-space: nowrap;
 display: flex;
 color: var(--n-jumper-text-color);
 transition: color .3s var(--n-bezier);
 align-items: center;
 font-size: var(--n-jumper-font-size);
 `,[P(`input`,`
 margin: var(--n-input-margin);
 width: var(--n-input-width);
 `)]),P(`pagination-item`,`
 position: relative;
 cursor: pointer;
 user-select: none;
 -webkit-user-select: none;
 display: flex;
 align-items: center;
 justify-content: center;
 box-sizing: border-box;
 min-width: var(--n-item-size);
 height: var(--n-item-size);
 padding: var(--n-item-padding);
 background-color: var(--n-item-color);
 color: var(--n-item-text-color);
 border-radius: var(--n-item-border-radius);
 border: var(--n-item-border);
 fill: var(--n-button-icon-color);
 transition:
 color .3s var(--n-bezier),
 border-color .3s var(--n-bezier),
 background-color .3s var(--n-bezier),
 fill .3s var(--n-bezier);
 `,[G(`button`,`
 background: var(--n-button-color);
 color: var(--n-button-icon-color);
 border: var(--n-button-border);
 padding: 0;
 `,[P(`base-icon`,`
 font-size: var(--n-button-icon-size);
 `)]),V(`disabled`,[G(`hover`,Lt,Rt),Z(`&:hover`,Lt,Rt),Z(`&:active`,`
 background: var(--n-item-color-pressed);
 color: var(--n-item-text-color-pressed);
 border: var(--n-item-border-pressed);
 `,[G(`button`,`
 background: var(--n-button-color-pressed);
 border: var(--n-button-border-pressed);
 color: var(--n-button-icon-color-pressed);
 `)]),G(`active`,`
 background: var(--n-item-color-active);
 color: var(--n-item-text-color-active);
 border: var(--n-item-border-active);
 `,[Z(`&:hover`,`
 background: var(--n-item-color-active-hover);
 `)])]),G(`disabled`,`
 cursor: not-allowed;
 color: var(--n-item-text-color-disabled);
 `,[G(`active, button`,`
 background-color: var(--n-item-color-disabled);
 border: var(--n-item-border-disabled);
 `)])]),G(`disabled`,`
 cursor: not-allowed;
 `,[P(`pagination-quick-jumper`,`
 color: var(--n-jumper-text-color-disabled);
 `)]),G(`simple`,`
 display: flex;
 align-items: center;
 flex-wrap: nowrap;
 `,[P(`pagination-quick-jumper`,[P(`input`,`
 margin: 0;
 `)])])]);function Bt(e){if(!e)return 10;let{defaultPageSize:t}=e;if(t!==void 0)return t;let n=e.pageSizes?.[0];return typeof n==`number`?n:n?.value||10}function Vt(e,t,n,r){let i=!1,a=!1,o=1,s=t;if(t===1)return{hasFastBackward:!1,hasFastForward:!1,fastForwardTo:s,fastBackwardTo:o,items:[{type:`page`,label:1,active:e===1,mayBeFastBackward:!1,mayBeFastForward:!1}]};if(t===2)return{hasFastBackward:!1,hasFastForward:!1,fastForwardTo:s,fastBackwardTo:o,items:[{type:`page`,label:1,active:e===1,mayBeFastBackward:!1,mayBeFastForward:!1},{type:`page`,label:2,active:e===2,mayBeFastBackward:!0,mayBeFastForward:!1}]};let c=t,l=e,u=e,d=(n-5)/2;u+=Math.ceil(d),u=Math.min(Math.max(u,1+n-3),c-2),l-=Math.floor(d),l=Math.max(Math.min(l,c-n+3),3);let f=!1,p=!1;l>3&&(f=!0),u<c-2&&(p=!0);let m=[];m.push({type:`page`,label:1,active:e===1,mayBeFastBackward:!1,mayBeFastForward:!1}),f?(i=!0,o=l-1,m.push({type:`fast-backward`,active:!1,label:void 0,options:r?Ht(2,l-1):null})):c>=2&&m.push({type:`page`,label:2,mayBeFastBackward:!0,mayBeFastForward:!1,active:e===2});for(let t=l;t<=u;++t)m.push({type:`page`,label:t,mayBeFastBackward:!1,mayBeFastForward:!1,active:e===t});return p?(a=!0,s=u+1,m.push({type:`fast-forward`,active:!1,label:void 0,options:r?Ht(u+1,c-1):null})):u===c-2&&m[m.length-1].label!==c-1&&m.push({type:`page`,mayBeFastForward:!0,mayBeFastBackward:!1,label:c-1,active:e===c-1}),m[m.length-1].label!==c&&m.push({type:`page`,mayBeFastForward:!1,mayBeFastBackward:!1,label:c,active:e===c}),{hasFastBackward:i,hasFastForward:a,fastBackwardTo:o,fastForwardTo:s,items:m}}function Ht(e,t){let n=[];for(let r=e;r<=t;++r)n.push({label:`${r}`,value:r});return n}var Ut=s({name:`Pagination`,props:Object.assign(Object.assign({},D.props),{simple:Boolean,page:Number,defaultPage:{type:Number,default:1},itemCount:Number,pageCount:Number,defaultPageCount:{type:Number,default:1},showSizePicker:Boolean,pageSize:Number,defaultPageSize:Number,pageSizes:{type:Array,default(){return[10]}},showQuickJumper:Boolean,size:String,disabled:Boolean,pageSlot:{type:Number,default:9},selectProps:Object,prev:Function,next:Function,goto:Function,prefix:Function,suffix:Function,label:Function,displayOrder:{type:Array,default:[`pages`,`size-picker`,`quick-jumper`]},to:oe.propTo,showQuickJumpDropdown:{type:Boolean,default:!0},scrollbarProps:Object,"onUpdate:page":[Function,Array],onUpdatePage:[Function,Array],"onUpdate:pageSize":[Function,Array],onUpdatePageSize:[Function,Array],onPageSizeChange:[Function,Array],onChange:[Function,Array]}),slots:Object,setup(t){let{mergedComponentPropsRef:n,mergedClsPrefixRef:r,inlineThemeDisabled:i,mergedRtlRef:a}=K(t),o=d(()=>t.size||n?.value?.Pagination?.size||`medium`),s=D(`Pagination`,`-pagination`,zt,It,t,r),{localeRef:l}=we(`Pagination`),u=e(null),f=e(t.defaultPage),p=e(Bt(t)),m=Se(_(t,`page`),f),g=Se(_(t,`pageSize`),p),v=d(()=>{let{itemCount:e}=t;if(e!==void 0)return Math.max(1,Math.ceil(e/g.value));let{pageCount:n}=t;return n===void 0?1:Math.max(n,1)}),y=e(``);h(()=>{t.simple,y.value=String(m.value)});let b=e(!1),x=e(!1),C=e(!1),w=e(!1),T=()=>{t.disabled||(b.value=!0,B())},E=()=>{t.disabled||(b.value=!1,B())},O=()=>{x.value=!0,B()},k=()=>{x.value=!1,B()},A=e=>{V(e)},j=d(()=>Vt(m.value,v.value,t.pageSlot,t.showQuickJumpDropdown));h(()=>{j.value.hasFastBackward?j.value.hasFastForward||(b.value=!1,C.value=!1):(x.value=!1,w.value=!1)});let M=d(()=>{let e=l.value.selectionSuffix;return t.pageSizes.map(t=>typeof t==`number`?{label:`${t} / ${e}`,value:t}:t)}),N=d(()=>n?.value?.Pagination?.inputSize||He(o.value)),P=d(()=>n?.value?.Pagination?.selectSize||He(o.value)),F=d(()=>(m.value-1)*g.value),I=d(()=>{let e=m.value*g.value-1,{itemCount:n}=t;return n===void 0?e:e>n-1?n-1:e}),L=d(()=>{let{itemCount:e}=t;return e===void 0?(t.pageCount||1)*g.value:e}),z=U(`Pagination`,a,r);function B(){c(()=>{var e;let{value:t}=u;t&&(t.classList.add(`transition-disabled`),(e=u.value)==null||e.offsetWidth,t.classList.remove(`transition-disabled`))})}function V(e){if(e===m.value)return;let{"onUpdate:page":n,onUpdatePage:r,onChange:i,simple:a}=t;n&&S(n,e),r&&S(r,e),i&&S(i,e),f.value=e,a&&(y.value=String(e))}function H(e){if(e===g.value)return;let{"onUpdate:pageSize":n,onUpdatePageSize:r,onPageSizeChange:i}=t;n&&S(n,e),r&&S(r,e),i&&S(i,e),p.value=e,v.value<m.value&&V(v.value)}function W(){t.disabled||V(Math.min(m.value+1,v.value))}function ee(){t.disabled||V(Math.max(m.value-1,1))}function G(){t.disabled||V(Math.min(j.value.fastForwardTo,v.value))}function q(){t.disabled||V(Math.max(j.value.fastBackwardTo,1))}function J(e){H(e)}function Y(){let e=Number.parseInt(y.value);Number.isNaN(e)||(V(Math.max(1,Math.min(e,v.value))),t.simple||(y.value=``))}function te(){Y()}function ne(e){if(!t.disabled)switch(e.type){case`page`:V(e.label);break;case`fast-backward`:q();break;case`fast-forward`:G();break}}function Z(e){y.value=e.replace(/\D+/g,``)}h(()=>{m.value,g.value,B()});let re=d(()=>{let e=o.value,{self:{buttonBorder:t,buttonBorderHover:n,buttonBorderPressed:r,buttonIconColor:i,buttonIconColorHover:a,buttonIconColorPressed:c,itemTextColor:l,itemTextColorHover:u,itemTextColorPressed:d,itemTextColorActive:f,itemTextColorDisabled:p,itemColor:m,itemColorHover:h,itemColorPressed:g,itemColorActive:_,itemColorActiveHover:v,itemColorDisabled:y,itemBorder:b,itemBorderHover:x,itemBorderPressed:S,itemBorderActive:C,itemBorderDisabled:w,itemBorderRadius:T,jumperTextColor:E,jumperTextColorDisabled:D,buttonColor:O,buttonColorHover:k,buttonColorPressed:A,[R(`itemPadding`,e)]:j,[R(`itemMargin`,e)]:M,[R(`inputWidth`,e)]:N,[R(`selectWidth`,e)]:P,[R(`inputMargin`,e)]:F,[R(`selectMargin`,e)]:I,[R(`jumperFontSize`,e)]:L,[R(`prefixMargin`,e)]:z,[R(`suffixMargin`,e)]:B,[R(`itemSize`,e)]:V,[R(`buttonIconSize`,e)]:H,[R(`itemFontSize`,e)]:U,[`${R(`itemMargin`,e)}Rtl`]:W,[`${R(`inputMargin`,e)}Rtl`]:ee},common:{cubicBezierEaseInOut:G}}=s.value;return{"--n-prefix-margin":z,"--n-suffix-margin":B,"--n-item-font-size":U,"--n-select-width":P,"--n-select-margin":I,"--n-input-width":N,"--n-input-margin":F,"--n-input-margin-rtl":ee,"--n-item-size":V,"--n-item-text-color":l,"--n-item-text-color-disabled":p,"--n-item-text-color-hover":u,"--n-item-text-color-active":f,"--n-item-text-color-pressed":d,"--n-item-color":m,"--n-item-color-hover":h,"--n-item-color-disabled":y,"--n-item-color-active":_,"--n-item-color-active-hover":v,"--n-item-color-pressed":g,"--n-item-border":b,"--n-item-border-hover":x,"--n-item-border-disabled":w,"--n-item-border-active":C,"--n-item-border-pressed":S,"--n-item-padding":j,"--n-item-border-radius":T,"--n-bezier":G,"--n-jumper-font-size":L,"--n-jumper-text-color":E,"--n-jumper-text-color-disabled":D,"--n-item-margin":M,"--n-item-margin-rtl":W,"--n-button-icon-size":H,"--n-button-icon-color":i,"--n-button-icon-color-hover":a,"--n-button-icon-color-pressed":c,"--n-button-color-hover":k,"--n-button-color":O,"--n-button-color-pressed":A,"--n-button-border":t,"--n-button-border-hover":n,"--n-button-border-pressed":r}}),Q=i?X(`pagination`,d(()=>{let e=``;return e+=o.value[0],e}),re,t):void 0;return{rtlEnabled:z,mergedClsPrefix:r,locale:l,selfRef:u,mergedPage:m,pageItems:d(()=>j.value.items),mergedItemCount:L,jumperValue:y,pageSizeOptions:M,mergedPageSize:g,inputSize:N,selectSize:P,mergedTheme:s,mergedPageCount:v,startIndex:F,endIndex:I,showFastForwardMenu:C,showFastBackwardMenu:w,fastForwardActive:b,fastBackwardActive:x,handleMenuSelect:A,handleFastForwardMouseenter:T,handleFastForwardMouseleave:E,handleFastBackwardMouseenter:O,handleFastBackwardMouseleave:k,handleJumperInput:Z,handleBackwardClick:ee,handleForwardClick:W,handlePageItemClick:ne,handleSizePickerChange:J,handleQuickJumperChange:te,cssVars:i?void 0:re,themeClass:Q?.themeClass,onRender:Q?.onRender}},render(){let{$slots:e,mergedClsPrefix:n,disabled:r,cssVars:i,mergedPage:a,mergedPageCount:o,pageItems:s,showSizePicker:c,showQuickJumper:l,mergedTheme:u,locale:d,inputSize:f,selectSize:m,mergedPageSize:h,pageSizeOptions:g,jumperValue:_,simple:v,prev:y,next:b,prefix:x,suffix:S,label:w,goto:T,handleJumperInput:E,handleSizePickerChange:D,handleBackwardClick:O,handlePageItemClick:k,handleForwardClick:A,handleQuickJumperChange:j,onRender:M}=this;M?.();let N=x||e.prefix,P=S||e.suffix,F=y||e.prev,I=b||e.next,L=w||e.label;return t(`div`,{ref:`selfRef`,class:[`${n}-pagination`,this.themeClass,this.rtlEnabled&&`${n}-pagination--rtl`,r&&`${n}-pagination--disabled`,v&&`${n}-pagination--simple`],style:i},N?t(`div`,{class:`${n}-pagination-prefix`},N({page:a,pageSize:h,pageCount:o,startIndex:this.startIndex,endIndex:this.endIndex,itemCount:this.mergedItemCount})):null,this.displayOrder.map(e=>{switch(e){case`pages`:return t(p,null,t(`div`,{class:[`${n}-pagination-item`,!F&&`${n}-pagination-item--button`,(a<=1||a>o||r)&&`${n}-pagination-item--disabled`],onClick:O},F?F({page:a,pageSize:h,pageCount:o,startIndex:this.startIndex,endIndex:this.endIndex,itemCount:this.mergedItemCount}):t(C,{clsPrefix:n},{default:()=>this.rtlEnabled?t(Ye,null):t(We,null)})),v?t(p,null,t(`div`,{class:`${n}-pagination-quick-jumper`},t(De,{value:_,onUpdateValue:E,size:f,placeholder:``,disabled:r,theme:u.peers.Input,themeOverrides:u.peerOverrides.Input,onChange:j})),`\xA0/`,` `,o):s.map((e,i)=>{let a,o,s,{type:c}=e;switch(c){case`page`:let r=e.label;a=L?L({type:`page`,node:r,active:e.active}):r;break;case`fast-forward`:let i=this.fastForwardActive?t(C,{clsPrefix:n},{default:()=>this.rtlEnabled?t(qe,null):t(Je,null)}):t(C,{clsPrefix:n},{default:()=>t(Xe,null)});a=L?L({type:`fast-forward`,node:i,active:this.fastForwardActive||this.showFastForwardMenu}):i,o=this.handleFastForwardMouseenter,s=this.handleFastForwardMouseleave;break;case`fast-backward`:let c=this.fastBackwardActive?t(C,{clsPrefix:n},{default:()=>this.rtlEnabled?t(Je,null):t(qe,null)}):t(C,{clsPrefix:n},{default:()=>t(Xe,null)});a=L?L({type:`fast-backward`,node:c,active:this.fastBackwardActive||this.showFastBackwardMenu}):c,o=this.handleFastBackwardMouseenter,s=this.handleFastBackwardMouseleave;break}let l=t(`div`,{key:i,class:[`${n}-pagination-item`,e.active&&`${n}-pagination-item--active`,c!==`page`&&(c===`fast-backward`&&this.showFastBackwardMenu||c===`fast-forward`&&this.showFastForwardMenu)&&`${n}-pagination-item--hover`,r&&`${n}-pagination-item--disabled`,c===`page`&&`${n}-pagination-item--clickable`],onClick:()=>{k(e)},onMouseenter:o,onMouseleave:s},a);if(c===`page`&&!e.mayBeFastBackward&&!e.mayBeFastForward)return l;{let n=e.type===`page`?e.mayBeFastBackward?`fast-backward`:`fast-forward`:e.type;return e.type!==`page`&&!e.options?l:t(kt,{to:this.to,key:n,disabled:r,trigger:`hover`,virtualScroll:!0,style:{width:`60px`},theme:u.peers.Popselect,themeOverrides:u.peerOverrides.Popselect,builtinThemeOverrides:{peers:{InternalSelectMenu:{height:`calc(var(--n-option-height) * 4.6)`}}},nodeProps:()=>({style:{justifyContent:`center`}}),show:c===`page`?!1:c===`fast-backward`?this.showFastBackwardMenu:this.showFastForwardMenu,onUpdateShow:e=>{c!==`page`&&(e?c===`fast-backward`?this.showFastBackwardMenu=e:this.showFastForwardMenu=e:(this.showFastBackwardMenu=!1,this.showFastForwardMenu=!1))},options:e.type!==`page`&&e.options?e.options:[],onUpdateValue:this.handleMenuSelect,scrollable:!0,scrollbarProps:this.scrollbarProps,showCheckmark:!1},{default:()=>l})}}),t(`div`,{class:[`${n}-pagination-item`,!I&&`${n}-pagination-item--button`,{[`${n}-pagination-item--disabled`]:a<1||a>=o||r}],onClick:A},I?I({page:a,pageSize:h,pageCount:o,itemCount:this.mergedItemCount,startIndex:this.startIndex,endIndex:this.endIndex}):t(C,{clsPrefix:n},{default:()=>this.rtlEnabled?t(We,null):t(Ye,null)})));case`size-picker`:return!v&&c?t(Nt,Object.assign({consistentMenuWidth:!1,placeholder:``,showCheckmark:!1,to:this.to},this.selectProps,{size:m,options:g,value:h,disabled:r,scrollbarProps:this.scrollbarProps,theme:u.peers.Select,themeOverrides:u.peerOverrides.Select,onUpdateValue:D})):null;case`quick-jumper`:return!v&&l?t(`div`,{class:`${n}-pagination-quick-jumper`},T?T():re(this.$slots.goto,()=>[d.goto]),t(De,{value:_,onUpdateValue:E,size:f,placeholder:``,disabled:r,theme:u.peers.Input,themeOverrides:u.peerOverrides.Input,onChange:j})):null;default:return null}}),P?t(`div`,{class:`${n}-pagination-suffix`},P({page:a,pageSize:h,pageCount:o,startIndex:this.startIndex,endIndex:this.endIndex,itemCount:this.mergedItemCount})):null)}});export{nt as n,Ut as t};