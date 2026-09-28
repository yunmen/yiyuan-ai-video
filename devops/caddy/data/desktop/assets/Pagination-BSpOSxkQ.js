import{$ as e,B as t,E as n,F as r,G as i,I as a,L as o,M as s,N as c,O as l,W as u,Z as d,d as f,j as p,k as m,m as h,q as g,s as _,v}from"./vue-vendor-VvR516j_.js";import{Bt as y,Ct as b,D as x,Dt as S,E as C,Ft as w,It as T,Mt as E,O as D,Rt as O,St as k,Xt as A,Zt as j,bt as M,cn as N,dn as P,en as F,f as I,ft as L,gn as R,gt as z,h as B,hn as V,in as H,j as U,l as W,ln as ee,mn as G,mt as te,on as K,p as q,pn as J,pt as Y,sn as ne,u as re,un as X,vt as ie,wt as Z,xt as Q}from"./initial-vendor-DGcJKj6B.js";import{c as ae,d as oe,f as se,g as ce,i as le,l as ue,m as de,n as fe,p as pe,s as me,t as he,u as ge}from"./Popover-B5gZpOZf.js";import{a as _e,i as ve,o as ye,r as be,s as $,t as xe}from"./Tag-DvPR2RNT.js";import{t as Se}from"./use-merged-state-D72VTG8A.js";import{t as Ce}from"./use-compitable-BRZdiTRV.js";import{n as we}from"./Eye-Czh4ydd5.js";import{n as Te,r as Ee,t as De}from"./Input-PA0fYZaM.js";import{n as Oe,t as ke}from"./Empty-CDlZy4qr.js";function Ae(e){return e&-e}var je=class{constructor(e,t){this.l=e,this.min=t;let n=Array(e+1);for(let t=0;t<e+1;++t)n[t]=0;this.ft=n}add(e,t){if(t===0)return;let{l:n,ft:r}=this;for(e+=1;e<=n;)r[e]+=t,e+=Ae(e)}get(e){return this.sum(e+1)-this.sum(e)}sum(e){if(e===void 0&&(e=this.l),e<=0)return 0;let{ft:t,min:n,l:r}=this;if(e>r)throw Error("[FinweckTree.sum]: `i` is larger than length.");let i=e*n;for(;e>0;)i+=t[e],e-=Ae(e);return i}getBound(e){let t=0,n=this.l;for(;n>t;){let r=Math.floor((t+n)/2),i=this.sum(r);if(i>e){n=r;continue}else if(i<e){if(t===r)return this.sum(t+1)<=e?t+1:r;t=r}else return r}return t}},Me;function Ne(){return typeof document>`u`?!1:(Me===void 0&&(Me=`matchMedia`in window?window.matchMedia(`(pointer:coarse)`).matches:!1),Me)}var Pe;function Fe(){return typeof document>`u`?1:(Pe===void 0&&(Pe=`chrome`in window?window.devicePixelRatio:1),Pe)}var Ie=`VVirtualListXScroll`;function Le({columnsRef:e,renderColRef:n,renderItemWithColsRef:r}){let i=d(0),a=d(0),o=v(()=>{let t=e.value;if(t.length===0)return null;let n=new je(t.length,0);return t.forEach((e,t)=>{n.add(t,e.width)}),n});return t(Ie,{startIndexRef:F(()=>{let e=o.value;return e===null?0:Math.max(e.getBound(a.value)-1,0)}),endIndexRef:F(()=>{let t=o.value;return t===null?0:Math.min(t.getBound(a.value+i.value)+1,e.value.length-1)}),columnsRef:e,renderColRef:n,renderItemWithColsRef:r,getLeft:e=>{let t=o.value;return t===null?0:t.sum(e)}}),{listWidthRef:i,scrollLeftRef:a}}var Re=n({name:`VirtualListRow`,props:{index:{type:Number,required:!0},item:{type:Object,required:!0}},setup(){let{startIndexRef:e,endIndexRef:t,columnsRef:n,getLeft:r,renderColRef:i,renderItemWithColsRef:a}=m(Ie);return{startIndex:e,endIndex:t,columns:n,renderCol:i,renderItemWithCols:a,getLeft:r}},render(){let{startIndex:e,endIndex:t,columns:n,renderCol:r,renderItemWithCols:i,getLeft:a,item:o}=this;if(i!=null)return i({itemIndex:this.index,startColIndex:e,endColIndex:t,allColumns:n,item:o,getLeft:a});if(r!=null){let i=[];for(let s=e;s<=t;++s){let e=n[s];i.push(r({column:e,left:a(s),item:o}))}return i}return null}}),ze=ae(`.v-vl`,{maxHeight:`inherit`,height:`100%`,overflow:`auto`,minWidth:`1px`},[ae(`&:not(.v-vl--show-scrollbar)`,{scrollbarWidth:`none`},[ae(`&::-webkit-scrollbar, &::-webkit-scrollbar-track-piece, &::-webkit-scrollbar-thumb`,{width:0,height:0,display:`none`})])]),Be=n({name:`VirtualList`,inheritAttrs:!1,props:{showScrollbar:{type:Boolean,default:!0},columns:{type:Array,default:()=>[]},renderCol:Function,renderItemWithCols:Function,items:{type:Array,default:()=>[]},itemSize:{type:Number,required:!0},itemResizable:Boolean,itemsStyle:[String,Object],visibleItemsTag:{type:[String,Object],default:`div`},visibleItemsProps:Object,ignoreItemResize:Boolean,onScroll:Function,onWheel:Function,onResize:Function,defaultScrollKey:[Number,String],defaultScrollIndex:Number,keyField:{type:String,default:`key`},paddingTop:{type:[Number,String],default:0},paddingBottom:{type:[Number,String],default:0}},setup(t){let n=O();ze.mount({id:`vueuc/virtual-list`,head:!0,anchorMetaName:ue,ssr:n}),o(()=>{let{defaultScrollIndex:e,defaultScrollKey:n}=t;e==null?n!=null&&S({key:n}):S({index:e})});let r=!1,i=!1;c(()=>{if(r=!1,!i){i=!0;return}S({top:y.value,left:u.value})}),a(()=>{r=!0,i||=!0});let s=F(()=>{if(t.renderCol==null&&t.renderItemWithCols==null||t.columns.length===0)return;let e=0;return t.columns.forEach(t=>{e+=t.width}),e}),l=v(()=>{let e=new Map,{keyField:n}=t;return t.items.forEach((t,r)=>{e.set(t[n],r)}),e}),{scrollLeftRef:u,listWidthRef:f}=Le({columnsRef:e(t,`columns`),renderColRef:e(t,`renderCol`),renderItemWithColsRef:e(t,`renderItemWithCols`)}),p=d(null),m=d(void 0),h=new Map,g=v(()=>{let{items:e,itemSize:n,keyField:r}=t,i=new je(e.length,n);return e.forEach((e,t)=>{let n=e[r],a=h.get(n);a!==void 0&&i.add(t,a)}),i}),_=d(0),y=d(0),b=F(()=>Math.max(g.value.getBound(y.value-K(t.paddingTop))-1,0)),x=v(()=>{let{value:e}=m;if(e===void 0)return[];let{items:n,itemSize:r}=t,i=b.value,a=Math.min(i+Math.ceil(e/r+1),n.length-1),o=[];for(let e=i;e<=a;++e)o.push(n[e]);return o}),S=(e,t)=>{if(typeof e==`number`){E(e,t,`auto`);return}let{left:n,top:r,index:i,key:a,position:o,behavior:s,debounce:c=!0}=e;if(n!==void 0||r!==void 0)E(n,r,s);else if(i!==void 0)T(i,s,c);else if(a!==void 0){let e=l.value.get(a);e!==void 0&&T(e,s,c)}else o===`bottom`?E(0,2**53-1,s):o===`top`&&E(0,0,s)},C,w=null;function T(e,n,r){let{value:i}=g,a=i.sum(e)+K(t.paddingTop);if(!r)p.value.scrollTo({left:0,top:a,behavior:n});else{C=e,w!==null&&window.clearTimeout(w),w=window.setTimeout(()=>{C=void 0,w=null},16);let{scrollTop:t,offsetHeight:r}=p.value;if(a>t){let o=i.get(e);a+o<=t+r||p.value.scrollTo({left:0,top:a+o-r,behavior:n})}else p.value.scrollTo({left:0,top:a,behavior:n})}}function E(e,t,n){p.value.scrollTo({left:e,top:t,behavior:n})}function D(e,n){if(r||t.ignoreItemResize||L(n.target))return;let{value:i}=g,a=l.value.get(e),o=i.get(a),s=n.borderBoxSize?.[0]?.blockSize??n.contentRect.height;if(s===o)return;s-t.itemSize===0?h.delete(e):h.set(e,s-t.itemSize);let c=s-o;if(c===0)return;i.add(a,c);let u=p.value;if(u!=null){if(C===void 0){let e=i.sum(a);u.scrollTop>e&&u.scrollBy(0,c)}else (a<C||a===C&&s+i.sum(a)>u.scrollTop+u.offsetHeight)&&u.scrollBy(0,c);I()}_.value++}let k=!Ne(),A=!1;function j(e){var n;(n=t.onScroll)==null||n.call(t,e),(!k||!A)&&I()}function M(e){var n;if((n=t.onWheel)==null||n.call(t,e),k){let t=p.value;if(t!=null){if(e.deltaX===0&&(t.scrollTop===0&&e.deltaY<=0||t.scrollTop+t.offsetHeight>=t.scrollHeight&&e.deltaY>=0))return;e.preventDefault(),t.scrollTop+=e.deltaY/Fe(),t.scrollLeft+=e.deltaX/Fe(),I(),A=!0,ce(()=>{A=!1})}}}function P(e){if(r||L(e.target))return;if(t.renderCol==null&&t.renderItemWithCols==null){if(e.contentRect.height===m.value)return}else if(e.contentRect.height===m.value&&e.contentRect.width===f.value)return;m.value=e.contentRect.height,f.value=e.contentRect.width;let{onResize:n}=t;n!==void 0&&n(e)}function I(){let{value:e}=p;e!=null&&(y.value=e.scrollTop,u.value=e.scrollLeft)}function L(e){let t=e;for(;t!==null;){if(t.style.display===`none`)return!0;t=t.parentElement}return!1}return{listHeight:m,listStyle:{overflow:`auto`},keyToIndex:l,itemsStyle:v(()=>{let{itemResizable:e}=t,n=N(g.value.sum());return _.value,[t.itemsStyle,{boxSizing:`content-box`,width:N(s.value),height:e?``:n,minHeight:e?n:``,paddingTop:N(t.paddingTop),paddingBottom:N(t.paddingBottom)}]}),visibleItemsStyle:v(()=>(_.value,{transform:`translateY(${N(g.value.sum(b.value))})`})),viewportItems:x,listElRef:p,itemsElRef:d(null),scrollTo:S,handleListResize:P,handleListScroll:j,handleListWheel:M,handleItemResize:D}},render(){let{itemResizable:e,keyField:t,keyToIndex:n,visibleItemsTag:r}=this;return l(w,{onResize:this.handleListResize},{default:()=>{var i;return l(`div`,p(this.$attrs,{class:[`v-vl`,this.showScrollbar&&`v-vl--show-scrollbar`],onScroll:this.handleListScroll,onWheel:this.handleListWheel,ref:`listElRef`}),[this.items.length===0?(i=this.$slots).empty?.call(i):l(`div`,{ref:`itemsElRef`,class:`v-vl-items`,style:this.itemsStyle},[l(r,Object.assign({class:`v-vl-visible-items`,style:this.visibleItemsStyle},this.visibleItemsProps),{default:()=>{let{renderCol:r,renderItemWithCols:i}=this;return this.viewportItems.map(a=>{let o=a[t],s=n.get(o),c=r==null?void 0:l(Re,{index:s,item:a}),u=i==null?void 0:l(Re,{index:s,item:a}),d=this.$slots.default({item:a,renderedCols:c,renderedItemWithCols:u,index:s})[0];return e?l(w,{key:o,onResize:e=>this.handleItemResize(o,e)},{default:()=>d}):(d.key=o,d)})}})])])}})}});function Ve(e,t){t&&(o(()=>{let{value:n}=e;n&&T.registerHandler(n,t)}),u(e,(e,t)=>{t&&T.unregisterHandler(t)},{deep:!1}),r(()=>{let{value:t}=e;t&&T.unregisterHandler(t)}))}function He(e){switch(typeof e){case`string`:return e||void 0;case`number`:return String(e);default:return}}var Ue={tiny:`mini`,small:`tiny`,medium:`small`,large:`medium`,huge:`large`};function We(e){let t=Ue[e];if(t===void 0)throw Error(`${e} has no smaller size.`);return t}function Ge(e){let t=e.filter(e=>e!==void 0);if(t.length!==0)return t.length===1?t[0]:t=>{e.forEach(e=>{e&&e(t)})}}var Ke=n({name:`Backward`,render(){return l(`svg`,{viewBox:`0 0 20 20`,fill:`none`,xmlns:`http://www.w3.org/2000/svg`},l(`path`,{d:`M12.2674 15.793C11.9675 16.0787 11.4927 16.0672 11.2071 15.7673L6.20572 10.5168C5.9298 10.2271 5.9298 9.7719 6.20572 9.48223L11.2071 4.23177C11.4927 3.93184 11.9675 3.92031 12.2674 4.206C12.5673 4.49169 12.5789 4.96642 12.2932 5.26634L7.78458 9.99952L12.2932 14.7327C12.5789 15.0326 12.5673 15.5074 12.2674 15.793Z`,fill:`currentColor`}))}}),qe=n({name:`Checkmark`,render(){return l(`svg`,{xmlns:`http://www.w3.org/2000/svg`,viewBox:`0 0 16 16`},l(`g`,{fill:`none`},l(`path`,{d:`M14.046 3.486a.75.75 0 0 1-.032 1.06l-7.93 7.474a.85.85 0 0 1-1.188-.022l-2.68-2.72a.75.75 0 1 1 1.068-1.053l2.234 2.267l7.468-7.038a.75.75 0 0 1 1.06.032z`,fill:`currentColor`})))}}),Je=n({name:`FastBackward`,render(){return l(`svg`,{viewBox:`0 0 20 20`,version:`1.1`,xmlns:`http://www.w3.org/2000/svg`},l(`g`,{stroke:`none`,"stroke-width":`1`,fill:`none`,"fill-rule":`evenodd`},l(`g`,{fill:`currentColor`,"fill-rule":`nonzero`},l(`path`,{d:`M8.73171,16.7949 C9.03264,17.0795 9.50733,17.0663 9.79196,16.7654 C10.0766,16.4644 10.0634,15.9897 9.76243,15.7051 L4.52339,10.75 L17.2471,10.75 C17.6613,10.75 17.9971,10.4142 17.9971,10 C17.9971,9.58579 17.6613,9.25 17.2471,9.25 L4.52112,9.25 L9.76243,4.29275 C10.0634,4.00812 10.0766,3.53343 9.79196,3.2325 C9.50733,2.93156 9.03264,2.91834 8.73171,3.20297 L2.31449,9.27241 C2.14819,9.4297 2.04819,9.62981 2.01448,9.8386 C2.00308,9.89058 1.99707,9.94459 1.99707,10 C1.99707,10.0576 2.00356,10.1137 2.01585,10.1675 C2.05084,10.3733 2.15039,10.5702 2.31449,10.7254 L8.73171,16.7949 Z`}))))}}),Ye=n({name:`FastForward`,render(){return l(`svg`,{viewBox:`0 0 20 20`,version:`1.1`,xmlns:`http://www.w3.org/2000/svg`},l(`g`,{stroke:`none`,"stroke-width":`1`,fill:`none`,"fill-rule":`evenodd`},l(`g`,{fill:`currentColor`,"fill-rule":`nonzero`},l(`path`,{d:`M11.2654,3.20511 C10.9644,2.92049 10.4897,2.93371 10.2051,3.23464 C9.92049,3.53558 9.93371,4.01027 10.2346,4.29489 L15.4737,9.25 L2.75,9.25 C2.33579,9.25 2,9.58579 2,10.0000012 C2,10.4142 2.33579,10.75 2.75,10.75 L15.476,10.75 L10.2346,15.7073 C9.93371,15.9919 9.92049,16.4666 10.2051,16.7675 C10.4897,17.0684 10.9644,17.0817 11.2654,16.797 L17.6826,10.7276 C17.8489,10.5703 17.9489,10.3702 17.9826,10.1614 C17.994,10.1094 18,10.0554 18,10.0000012 C18,9.94241 17.9935,9.88633 17.9812,9.83246 C17.9462,9.62667 17.8467,9.42976 17.6826,9.27455 L11.2654,3.20511 Z`}))))}}),Xe=n({name:`Forward`,render(){return l(`svg`,{viewBox:`0 0 20 20`,fill:`none`,xmlns:`http://www.w3.org/2000/svg`},l(`path`,{d:`M7.73271 4.20694C8.03263 3.92125 8.50737 3.93279 8.79306 4.23271L13.7944 9.48318C14.0703 9.77285 14.0703 10.2281 13.7944 10.5178L8.79306 15.7682C8.50737 16.0681 8.03263 16.0797 7.73271 15.794C7.43279 15.5083 7.42125 15.0336 7.70694 14.7336L12.2155 10.0005L7.70694 5.26729C7.42125 4.96737 7.43279 4.49264 7.73271 4.20694Z`,fill:`currentColor`}))}}),Ze=n({name:`More`,render(){return l(`svg`,{viewBox:`0 0 16 16`,version:`1.1`,xmlns:`http://www.w3.org/2000/svg`},l(`g`,{stroke:`none`,"stroke-width":`1`,fill:`none`,"fill-rule":`evenodd`},l(`g`,{fill:`currentColor`,"fill-rule":`nonzero`},l(`path`,{d:`M4,7 C4.55228,7 5,7.44772 5,8 C5,8.55229 4.55228,9 4,9 C3.44772,9 3,8.55229 3,8 C3,7.44772 3.44772,7 4,7 Z M8,7 C8.55229,7 9,7.44772 9,8 C9,8.55229 8.55229,9 8,9 C7.44772,9 7,8.55229 7,8 C7,7.44772 7.44772,7 8,7 Z M12,7 C12.5523,7 13,7.44772 13,8 C13,8.55229 12.5523,9 12,9 C11.4477,9 11,8.55229 11,8 C11,7.44772 11.4477,7 12,7 Z`}))))}}),Qe=n({props:{onFocus:Function,onBlur:Function},setup(e){return()=>l(`div`,{style:`width: 0; height: 0`,tabindex:0,onFocus:e.onFocus,onBlur:e.onBlur})}}),$e={height:`calc(var(--n-option-height) * 7.6)`,paddingTiny:`4px 0`,paddingSmall:`4px 0`,paddingMedium:`4px 0`,paddingLarge:`4px 0`,paddingHuge:`4px 0`,optionPaddingTiny:`0 12px`,optionPaddingSmall:`0 12px`,optionPaddingMedium:`0 12px`,optionPaddingLarge:`0 12px`,optionPaddingHuge:`0 12px`,loadingSize:`18px`};function et(e){let{borderRadius:t,popoverColor:n,textColor3:r,dividerColor:i,textColor2:a,primaryColorPressed:o,textColorDisabled:s,primaryColor:c,opacityDisabled:l,hoverColor:u,fontSizeTiny:d,fontSizeSmall:f,fontSizeMedium:p,fontSizeLarge:m,fontSizeHuge:h,heightTiny:g,heightSmall:_,heightMedium:v,heightLarge:y,heightHuge:b}=e;return Object.assign(Object.assign({},$e),{optionFontSizeTiny:d,optionFontSizeSmall:f,optionFontSizeMedium:p,optionFontSizeLarge:m,optionFontSizeHuge:h,optionHeightTiny:g,optionHeightSmall:_,optionHeightMedium:v,optionHeightLarge:y,optionHeightHuge:b,borderRadius:t,color:n,groupHeaderTextColor:r,actionDividerColor:i,optionTextColor:a,optionTextColorPressed:o,optionTextColorDisabled:s,optionTextColorActive:c,optionOpacityDisabled:l,optionCheckColor:c,optionColorPending:u,optionColorActive:`rgba(0, 0, 0, 0)`,optionColorActivePending:u,actionTextColor:a,loadingColor:c})}var tt=x({name:`InternalSelectMenu`,common:q,peers:{Scrollbar:I,Empty:Oe},self:et}),nt=n({name:`NBaseSelectGroupHeader`,props:{clsPrefix:{type:String,required:!0},tmNode:{type:Object,required:!0}},setup(){let{renderLabelRef:e,renderOptionRef:t,labelFieldRef:n,nodePropsRef:r}=m(de);return{labelField:n,nodeProps:r,renderLabel:e,renderOption:t}},render(){let{clsPrefix:e,renderLabel:t,renderOption:n,nodeProps:r,tmNode:{rawNode:i}}=this,a=r?.(i),o=t?t(i,!1):Q(i[this.labelField],i,!1),s=l(`div`,Object.assign({},a,{class:[`${e}-base-select-group-header`,a?.class]}),o);return i.render?i.render({node:s,option:i}):n?n({node:s,option:i,selected:!1}):s}});function rt(e,t){return l(_,{name:`fade-in-scale-up-transition`},{default:()=>e?l(C,{clsPrefix:t,class:`${t}-base-select-option__check`},{default:()=>l(qe)}):null})}var it=n({name:`NBaseSelectOption`,props:{clsPrefix:{type:String,required:!0},tmNode:{type:Object,required:!0}},setup(e){let{valueRef:t,pendingTmNodeRef:n,multipleRef:r,valueSetRef:i,renderLabelRef:a,renderOptionRef:o,labelFieldRef:s,valueFieldRef:c,showCheckmarkRef:l,nodePropsRef:u,handleOptionClick:d,handleOptionMouseEnter:f}=m(de),p=F(()=>{let{value:t}=n;return t?e.tmNode.key===t.key:!1});function h(t){let{tmNode:n}=e;n.disabled||d(t,n)}function g(t){let{tmNode:n}=e;n.disabled||f(t,n)}function _(t){let{tmNode:n}=e,{value:r}=p;n.disabled||r||f(t,n)}return{multiple:r,isGrouped:F(()=>{let{tmNode:t}=e,{parent:n}=t;return n&&n.rawNode.type===`group`}),showCheckmark:l,nodeProps:u,isPending:p,isSelected:F(()=>{let{value:n}=t,{value:a}=r;if(n===null)return!1;let o=e.tmNode.rawNode[c.value];if(a){let{value:e}=i;return e.has(o)}else return n===o}),labelField:s,renderLabel:a,renderOption:o,handleMouseMove:_,handleMouseEnter:g,handleClick:h}},render(){let{clsPrefix:e,tmNode:{rawNode:t},isSelected:n,isPending:r,isGrouped:i,showCheckmark:a,nodeProps:o,renderOption:s,renderLabel:c,handleClick:u,handleMouseEnter:d,handleMouseMove:f}=this,p=rt(n,e),m=c?[c(t,n),a&&p]:[Q(t[this.labelField],t,n),a&&p],h=o?.(t),g=l(`div`,Object.assign({},h,{class:[`${e}-base-select-option`,t.class,h?.class,{[`${e}-base-select-option--disabled`]:t.disabled,[`${e}-base-select-option--selected`]:n,[`${e}-base-select-option--grouped`]:i,[`${e}-base-select-option--pending`]:r,[`${e}-base-select-option--show-checkmark`]:a}],style:[h?.style||``,t.style||``],onClick:Ge([u,h?.onClick]),onMouseenter:Ge([d,h?.onMouseenter]),onMousemove:Ge([f,h?.onMousemove])}),l(`div`,{class:`${e}-base-select-option__content`},m));return t.render?t.render({node:g,option:t,selected:n}):s?s({node:g,option:t,selected:n}):g}}),at=P(`base-select-menu`,`
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
 `,[J(`content`,`
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
 `),J(`loading, empty`,`
 display: flex;
 padding: 12px 32px;
 flex: 1;
 justify-content: center;
 `),J(`loading`,`
 color: var(--n-loading-color);
 font-size: var(--n-loading-size);
 `),J(`header`,`
 padding: 8px var(--n-option-padding-left);
 font-size: var(--n-option-font-size);
 transition: 
 color .3s var(--n-bezier),
 border-color .3s var(--n-bezier);
 border-bottom: 1px solid var(--n-action-divider-color);
 color: var(--n-action-text-color);
 `),J(`action`,`
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
 `),X(`&::before`,`
 content: "";
 position: absolute;
 left: 4px;
 right: 4px;
 top: 0;
 bottom: 0;
 border-radius: var(--n-border-radius);
 transition: background-color .3s var(--n-bezier);
 `),X(`&:active`,`
 color: var(--n-option-text-color-pressed);
 `),G(`grouped`,`
 padding-left: calc(var(--n-option-padding-left) * 1.5);
 `),G(`pending`,[X(`&::before`,`
 background-color: var(--n-option-color-pending);
 `)]),G(`selected`,`
 color: var(--n-option-text-color-active);
 `,[X(`&::before`,`
 background-color: var(--n-option-color-active);
 `),G(`pending`,[X(`&::before`,`
 background-color: var(--n-option-color-active-pending);
 `)])]),G(`disabled`,`
 cursor: not-allowed;
 `,[V(`selected`,`
 color: var(--n-option-text-color-disabled);
 `),G(`selected`,`
 opacity: var(--n-option-opacity-disabled);
 `)]),J(`check`,`
 font-size: 16px;
 position: absolute;
 right: calc(var(--n-option-padding-right) - 4px);
 top: calc(50% - 7px);
 color: var(--n-option-check-color);
 transition: color .3s var(--n-bezier);
 `,[W({enterScale:`0.5`})])])]),ot=n({name:`InternalSelectMenu`,props:Object.assign(Object.assign({},D.props),{clsPrefix:{type:String,required:!0},scrollable:{type:Boolean,default:!0},treeMate:{type:Object,required:!0},multiple:Boolean,size:{type:String,default:`medium`},value:{type:[String,Number,Array],default:null},autoPending:Boolean,virtualScroll:{type:Boolean,default:!0},show:{type:Boolean,default:!0},labelField:{type:String,default:`label`},valueField:{type:String,default:`value`},loading:Boolean,focusable:Boolean,renderLabel:Function,renderOption:Function,nodeProps:Function,showCheckmark:{type:Boolean,default:!0},onMousedown:Function,onScroll:Function,onFocus:Function,onBlur:Function,onKeyup:Function,onKeydown:Function,onTabOut:Function,onMouseenter:Function,onMouseleave:Function,onResize:Function,resetMenuOnOptionsChange:{type:Boolean,default:!0},inlineThemeDisabled:Boolean,scrollbarProps:Object,onToggle:Function}),setup(n){let{mergedClsPrefixRef:i,mergedRtlRef:a,mergedComponentPropsRef:c}=te(n),l=U(`InternalSelectMenu`,a,i),f=D(`InternalSelectMenu`,`-internal-select-menu`,at,tt,n,e(n,`clsPrefix`)),p=d(null),m=d(null),h=d(null),g=v(()=>n.treeMate.getFlattenedNodes()),_=v(()=>ve(g.value)),y=d(null);function b(){let{treeMate:e}=n,t=null,{value:r}=n;r===null?t=e.getFirstAvailableNode():(t=n.multiple?e.getNode((r||[])[(r||[]).length-1]):e.getNode(r),(!t||t.disabled)&&(t=e.getFirstAvailableNode())),H(t||null)}function x(){let{value:e}=y;e&&!n.treeMate.getNode(e.key)&&(y.value=null)}let S;u(()=>n.show,e=>{e?S=u(()=>n.treeMate,()=>{n.resetMenuOnOptionsChange?(n.autoPending?b():x(),s(W)):x()},{immediate:!0}):S?.()},{immediate:!0}),r(()=>{S?.()});let C=v(()=>K(f.value.self[R(`optionHeight`,n.size)])),w=v(()=>ne(f.value.self[R(`padding`,n.size)])),T=v(()=>n.multiple&&Array.isArray(n.value)?new Set(n.value):new Set),E=v(()=>{let e=g.value;return e&&e.length===0}),O=v(()=>c?.value?.Select?.renderEmpty);function k(e){let{onToggle:t}=n;t&&t(e)}function A(e){let{onScroll:t}=n;t&&t(e)}function j(e){var t;(t=h.value)==null||t.sync(),A(e)}function M(){var e;(e=h.value)==null||e.sync()}function N(){let{value:e}=y;return e||null}function P(e,t){t.disabled||H(t,!1)}function F(e,t){t.disabled||k(t)}function I(e){var t;$(e,`action`)||(t=n.onKeyup)==null||t.call(n,e)}function L(e){var t;$(e,`action`)||(t=n.onKeydown)==null||t.call(n,e)}function z(e){var t;(t=n.onMousedown)==null||t.call(n,e),!n.focusable&&e.preventDefault()}function B(){let{value:e}=y;e&&H(e.getNext({loop:!0}),!0)}function V(){let{value:e}=y;e&&H(e.getPrev({loop:!0}),!0)}function H(e,t=!1){y.value=e,t&&W()}function W(){var e,t;let r=y.value;if(!r)return;let i=_.value(r.key);i!==null&&(n.virtualScroll?(e=m.value)==null||e.scrollTo({index:i}):(t=h.value)==null||t.scrollTo({index:i,elSize:C.value}))}function ee(e){var t;p.value?.contains(e.target)&&((t=n.onFocus)==null||t.call(n,e))}function G(e){var t;p.value?.contains(e.relatedTarget)||(t=n.onBlur)==null||t.call(n,e)}t(de,{handleOptionMouseEnter:P,handleOptionClick:F,valueSetRef:T,pendingTmNodeRef:y,nodePropsRef:e(n,`nodeProps`),showCheckmarkRef:e(n,`showCheckmark`),multipleRef:e(n,`multiple`),valueRef:e(n,`value`),renderLabelRef:e(n,`renderLabel`),renderOptionRef:e(n,`renderOption`),labelFieldRef:e(n,`labelField`),valueFieldRef:e(n,`valueField`)}),t(pe,p),o(()=>{let{value:e}=h;e&&e.sync()});let q=v(()=>{let{size:e}=n,{common:{cubicBezierEaseInOut:t},self:{height:r,borderRadius:i,color:a,groupHeaderTextColor:o,actionDividerColor:s,optionTextColorPressed:c,optionTextColor:l,optionTextColorDisabled:u,optionTextColorActive:d,optionOpacityDisabled:p,optionCheckColor:m,actionTextColor:h,optionColorPending:g,optionColorActive:_,loadingColor:v,loadingSize:y,optionColorActivePending:b,[R(`optionFontSize`,e)]:x,[R(`optionHeight`,e)]:S,[R(`optionPadding`,e)]:C}}=f.value;return{"--n-height":r,"--n-action-divider-color":s,"--n-action-text-color":h,"--n-bezier":t,"--n-border-radius":i,"--n-color":a,"--n-option-font-size":x,"--n-group-header-text-color":o,"--n-option-check-color":m,"--n-option-color-pending":g,"--n-option-color-active":_,"--n-option-color-active-pending":b,"--n-option-height":S,"--n-option-opacity-disabled":p,"--n-option-text-color":l,"--n-option-text-color-active":d,"--n-option-text-color-disabled":u,"--n-option-text-color-pressed":c,"--n-option-padding":C,"--n-option-padding-left":ne(C,`left`),"--n-option-padding-right":ne(C,`right`),"--n-loading-color":v,"--n-loading-size":y}}),{inlineThemeDisabled:J}=n,re=J?Y(`internal-select-menu`,v(()=>n.size[0]),q,n):void 0,X={selfRef:p,next:B,prev:V,getPendingTmNode:N};return Ve(p,n.onResize),Object.assign({mergedTheme:f,mergedClsPrefix:i,rtlEnabled:l,virtualListRef:m,scrollbarRef:h,itemSize:C,padding:w,flattenedNodes:g,empty:E,mergedRenderEmpty:O,virtualListContainer(){let{value:e}=m;return e?.listElRef},virtualListContent(){let{value:e}=m;return e?.itemsElRef},doScroll:A,handleFocusin:ee,handleFocusout:G,handleKeyUp:I,handleKeyDown:L,handleMouseDown:z,handleVirtualListResize:M,handleVirtualListScroll:j,cssVars:J?void 0:q,themeClass:re?.themeClass,onRender:re?.onRender},X)},render(){let{$slots:e,virtualScroll:t,clsPrefix:n,mergedTheme:r,themeClass:i,onRender:a}=this;return a?.(),l(`div`,{ref:`selfRef`,tabindex:this.focusable?0:-1,class:[`${n}-base-select-menu`,`${n}-base-select-menu--${this.size}-size`,this.rtlEnabled&&`${n}-base-select-menu--rtl`,i,this.multiple&&`${n}-base-select-menu--multiple`],style:this.cssVars,onFocusin:this.handleFocusin,onFocusout:this.handleFocusout,onKeyup:this.handleKeyUp,onKeydown:this.handleKeyDown,onMousedown:this.handleMouseDown,onMouseenter:this.onMouseenter,onMouseleave:this.onMouseleave},M(e.header,e=>e&&l(`div`,{class:`${n}-base-select-menu__header`,"data-header":!0,key:`header`},e)),this.loading?l(`div`,{class:`${n}-base-select-menu__loading`},l(B,{clsPrefix:n,strokeWidth:20})):this.empty?l(`div`,{class:`${n}-base-select-menu__empty`,"data-empty":!0},ie(e.empty,()=>[this.mergedRenderEmpty?.call(this)||l(ke,{theme:r.peers.Empty,themeOverrides:r.peerOverrides.Empty,size:this.size})])):l(re,Object.assign({ref:`scrollbarRef`,theme:r.peers.Scrollbar,themeOverrides:r.peerOverrides.Scrollbar,scrollable:this.scrollable,container:t?this.virtualListContainer:void 0,content:t?this.virtualListContent:void 0,onScroll:t?void 0:this.doScroll},this.scrollbarProps),{default:()=>t?l(Be,{ref:`virtualListRef`,class:`${n}-virtual-list`,items:this.flattenedNodes,itemSize:this.itemSize,showScrollbar:!1,paddingTop:this.padding.top,paddingBottom:this.padding.bottom,onResize:this.handleVirtualListResize,onScroll:this.handleVirtualListScroll,itemResizable:!0},{default:({item:e})=>e.isGroup?l(nt,{key:e.key,clsPrefix:n,tmNode:e}):e.ignored?null:l(it,{clsPrefix:n,key:e.key,tmNode:e})}):l(`div`,{class:`${n}-base-select-menu-option-wrapper`,style:{paddingTop:this.padding.top,paddingBottom:this.padding.bottom}},this.flattenedNodes.map(e=>e.isGroup?l(nt,{key:e.key,clsPrefix:n,tmNode:e}):l(it,{clsPrefix:n,key:e.key,tmNode:e})))}),M(e.action,e=>e&&[l(`div`,{class:`${n}-base-select-menu__action`,"data-action":!0,key:`action`},e),l(Qe,{onFocus:this.onTabOut,key:`focus-detector`})]))}}),st={paddingSingle:`0 26px 0 12px`,paddingMultiple:`3px 26px 0 12px`,clearSize:`16px`,arrowSize:`16px`};function ct(e){let{borderRadius:t,textColor2:n,textColorDisabled:r,inputColor:i,inputColorDisabled:a,primaryColor:o,primaryColorHover:s,warningColor:c,warningColorHover:l,errorColor:u,errorColorHover:d,borderColor:f,iconColor:p,iconColorDisabled:m,clearColor:h,clearColorHover:g,clearColorPressed:_,placeholderColor:v,placeholderColorDisabled:y,fontSizeTiny:b,fontSizeSmall:x,fontSizeMedium:S,fontSizeLarge:C,heightTiny:w,heightSmall:T,heightMedium:E,heightLarge:D,fontWeight:O}=e;return Object.assign(Object.assign({},st),{fontSizeTiny:b,fontSizeSmall:x,fontSizeMedium:S,fontSizeLarge:C,heightTiny:w,heightSmall:T,heightMedium:E,heightLarge:D,borderRadius:t,fontWeight:O,textColor:n,textColorDisabled:r,placeholderColor:v,placeholderColorDisabled:y,color:i,colorDisabled:a,colorActive:i,border:`1px solid ${f}`,borderHover:`1px solid ${s}`,borderActive:`1px solid ${o}`,borderFocus:`1px solid ${s}`,boxShadowHover:`none`,boxShadowActive:`0 0 0 2px ${H(o,{alpha:.2})}`,boxShadowFocus:`0 0 0 2px ${H(o,{alpha:.2})}`,caretColor:o,arrowColor:p,arrowColorDisabled:m,loadingColor:o,borderWarning:`1px solid ${c}`,borderHoverWarning:`1px solid ${l}`,borderActiveWarning:`1px solid ${c}`,borderFocusWarning:`1px solid ${l}`,boxShadowHoverWarning:`none`,boxShadowActiveWarning:`0 0 0 2px ${H(c,{alpha:.2})}`,boxShadowFocusWarning:`0 0 0 2px ${H(c,{alpha:.2})}`,colorActiveWarning:i,caretColorWarning:c,borderError:`1px solid ${u}`,borderHoverError:`1px solid ${d}`,borderActiveError:`1px solid ${u}`,borderFocusError:`1px solid ${d}`,boxShadowHoverError:`none`,boxShadowActiveError:`0 0 0 2px ${H(u,{alpha:.2})}`,boxShadowFocusError:`0 0 0 2px ${H(u,{alpha:.2})}`,colorActiveError:i,caretColorError:u,clearColor:h,clearColorHover:g,clearColorPressed:_})}var lt=x({name:`InternalSelection`,common:q,peers:{Popover:le},self:ct}),ut=X([P(`base-selection`,`
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
 `),P(`base-selection-tags`,`min-height: var(--n-height);`),J(`border, state-border`,`
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
 `),J(`state-border`,`
 z-index: 1;
 border-color: #0000;
 `),P(`base-suffix`,`
 cursor: pointer;
 position: absolute;
 top: 50%;
 transform: translateY(-50%);
 right: 10px;
 `,[J(`arrow`,`
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
 `,[J(`wrapper`,`
 flex-basis: 0;
 flex-grow: 1;
 overflow: hidden;
 text-overflow: ellipsis;
 `)]),P(`base-selection-placeholder`,`
 color: var(--n-placeholder-color);
 `,[J(`inner`,`
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
 `,[J(`content`,`
 text-overflow: ellipsis;
 overflow: hidden;
 white-space: nowrap; 
 `)]),J(`render-label`,`
 color: var(--n-text-color);
 `)]),V(`disabled`,[X(`&:hover`,[J(`state-border`,`
 box-shadow: var(--n-box-shadow-hover);
 border: var(--n-border-hover);
 `)]),G(`focus`,[J(`state-border`,`
 box-shadow: var(--n-box-shadow-focus);
 border: var(--n-border-focus);
 `)]),G(`active`,[J(`state-border`,`
 box-shadow: var(--n-box-shadow-active);
 border: var(--n-border-active);
 `),P(`base-selection-label`,`background-color: var(--n-color-active);`),P(`base-selection-tags`,`background-color: var(--n-color-active);`)])]),G(`disabled`,`cursor: not-allowed;`,[J(`arrow`,`
 color: var(--n-arrow-color-disabled);
 `),P(`base-selection-label`,`
 cursor: not-allowed;
 background-color: var(--n-color-disabled);
 `,[P(`base-selection-input`,`
 cursor: not-allowed;
 color: var(--n-text-color-disabled);
 `),J(`render-label`,`
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
 `,[J(`input`,`
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
 `),J(`mirror`,`
 position: absolute;
 left: 0;
 top: 0;
 white-space: pre;
 visibility: hidden;
 user-select: none;
 -webkit-user-select: none;
 opacity: 0;
 `)]),[`warning`,`error`].map(e=>G(`${e}-status`,[J(`state-border`,`border: var(--n-border-${e});`),V(`disabled`,[X(`&:hover`,[J(`state-border`,`
 box-shadow: var(--n-box-shadow-hover-${e});
 border: var(--n-border-hover-${e});
 `)]),G(`active`,[J(`state-border`,`
 box-shadow: var(--n-box-shadow-active-${e});
 border: var(--n-border-active-${e});
 `),P(`base-selection-label`,`background-color: var(--n-color-active-${e});`),P(`base-selection-tags`,`background-color: var(--n-color-active-${e});`)]),G(`focus`,[J(`state-border`,`
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
 `,[X(`&:last-child`,`padding-right: 0;`),P(`tag`,`
 font-size: 14px;
 max-width: 100%;
 `,[J(`content`,`
 line-height: 1.25;
 text-overflow: ellipsis;
 overflow: hidden;
 `)])])]),dt=n({name:`InternalSelection`,props:Object.assign(Object.assign({},D.props),{clsPrefix:{type:String,required:!0},bordered:{type:Boolean,default:void 0},active:Boolean,pattern:{type:String,default:``},placeholder:String,selectedOption:{type:Object,default:null},selectedOptions:{type:Array,default:null},labelField:{type:String,default:`label`},valueField:{type:String,default:`value`},multiple:Boolean,filterable:Boolean,clearable:Boolean,disabled:Boolean,size:{type:String,default:`medium`},loading:Boolean,autofocus:Boolean,showArrow:{type:Boolean,default:!0},inputProps:Object,focused:Boolean,renderTag:Function,onKeydown:Function,onClick:Function,onBlur:Function,onFocus:Function,onDeleteOption:Function,maxTagCount:[String,Number],ellipsisTagPopoverProps:Object,onClear:Function,onPatternInput:Function,onPatternFocus:Function,onPatternBlur:Function,renderLabel:Function,status:String,inlineThemeDisabled:Boolean,ignoreComposition:{type:Boolean,default:!0},onResize:Function}),setup(t){let{mergedClsPrefixRef:n,mergedRtlRef:r}=te(t),a=U(`InternalSelection`,r,n),c=d(null),l=d(null),f=d(null),p=d(null),m=d(null),h=d(null),g=d(null),_=d(null),y=d(null),b=d(null),x=d(!1),S=d(!1),C=d(!1),w=D(`InternalSelection`,`-internal-selection`,ut,lt,t,e(t,`clsPrefix`)),T=v(()=>t.clearable&&!t.disabled&&(C.value||t.active)),E=v(()=>t.selectedOption?t.renderTag?t.renderTag({option:t.selectedOption,handleClose:()=>{}}):t.renderLabel?t.renderLabel(t.selectedOption,!0):Q(t.selectedOption[t.labelField],t.selectedOption,!0):t.placeholder),O=v(()=>{let e=t.selectedOption;if(e)return e[t.labelField]}),k=v(()=>t.multiple?!!(Array.isArray(t.selectedOptions)&&t.selectedOptions.length):t.selectedOption!==null);function A(){var e;let{value:n}=c;if(n){let{value:r}=l;r&&(r.style.width=`${n.offsetWidth}px`,t.maxTagCount!==`responsive`&&((e=y.value)==null||e.sync({showAllItemsBeforeCalculate:!1})))}}function j(){let{value:e}=b;e&&(e.style.display=`none`)}function M(){let{value:e}=b;e&&(e.style.display=`inline-block`)}u(e(t,`active`),e=>{e||j()}),u(e(t,`pattern`),()=>{t.multiple&&s(A)});function N(e){let{onFocus:n}=t;n&&n(e)}function P(e){let{onBlur:n}=t;n&&n(e)}function F(e){let{onDeleteOption:n}=t;n&&n(e)}function I(e){let{onClear:n}=t;n&&n(e)}function L(e){let{onPatternInput:n}=t;n&&n(e)}function z(e){(!e.relatedTarget||!f.value?.contains(e.relatedTarget))&&N(e)}function B(e){f.value?.contains(e.relatedTarget)||P(e)}function V(e){I(e)}function H(){C.value=!0}function W(){C.value=!1}function ee(e){!t.active||!t.filterable||e.target!==l.value&&e.preventDefault()}function G(e){F(e)}let K=d(!1);function q(e){if(e.key===`Backspace`&&!K.value&&!t.pattern.length){let{selectedOptions:e}=t;e?.length&&G(e[e.length-1])}}let J=null;function re(e){let{value:n}=c;n&&(n.textContent=e.target.value,A()),t.ignoreComposition&&K.value?J=e:L(e)}function X(){K.value=!0}function ie(){K.value=!1,t.ignoreComposition&&L(J),J=null}function Z(e){var n;S.value=!0,(n=t.onPatternFocus)==null||n.call(t,e)}function ae(e){var n;S.value=!1,(n=t.onPatternBlur)==null||n.call(t,e)}function oe(){var e,n;if(t.filterable)S.value=!1,(e=h.value)==null||e.blur(),(n=l.value)==null||n.blur();else if(t.multiple){let{value:e}=p;e?.blur()}else{let{value:e}=m;e?.blur()}}function se(){var e,n,r;t.filterable?(S.value=!1,(e=h.value)==null||e.focus()):t.multiple?(n=p.value)==null||n.focus():(r=m.value)==null||r.focus()}function ce(){let{value:e}=l;e&&(M(),e.focus())}function le(){let{value:e}=l;e&&e.blur()}function ue(e){let{value:t}=g;t&&t.setTextContent(`+${e}`)}function de(){let{value:e}=_;return e}function fe(){return l.value}let pe=null;function me(){pe!==null&&window.clearTimeout(pe)}function he(){t.active||(me(),pe=window.setTimeout(()=>{k.value&&(x.value=!0)},100))}function ge(){me()}function _e(e){e||(me(),x.value=!1)}u(k,e=>{e||(x.value=!1)}),o(()=>{i(()=>{let e=h.value;e&&(t.disabled?e.removeAttribute(`tabindex`):e.tabIndex=S.value?-1:0)})}),Ve(f,t.onResize);let{inlineThemeDisabled:ve}=t,ye=v(()=>{let{size:e}=t,{common:{cubicBezierEaseInOut:n},self:{fontWeight:r,borderRadius:i,color:a,placeholderColor:o,textColor:s,paddingSingle:c,paddingMultiple:l,caretColor:u,colorDisabled:d,textColorDisabled:f,placeholderColorDisabled:p,colorActive:m,boxShadowFocus:h,boxShadowActive:g,boxShadowHover:_,border:v,borderFocus:y,borderHover:b,borderActive:x,arrowColor:S,arrowColorDisabled:C,loadingColor:T,colorActiveWarning:E,boxShadowFocusWarning:D,boxShadowActiveWarning:O,boxShadowHoverWarning:k,borderWarning:A,borderFocusWarning:j,borderHoverWarning:M,borderActiveWarning:N,colorActiveError:P,boxShadowFocusError:F,boxShadowActiveError:I,boxShadowHoverError:L,borderError:z,borderFocusError:B,borderHoverError:V,borderActiveError:H,clearColor:U,clearColorHover:W,clearColorPressed:ee,clearSize:G,arrowSize:te,[R(`height`,e)]:K,[R(`fontSize`,e)]:q}}=w.value,J=ne(c),Y=ne(l);return{"--n-bezier":n,"--n-border":v,"--n-border-active":x,"--n-border-focus":y,"--n-border-hover":b,"--n-border-radius":i,"--n-box-shadow-active":g,"--n-box-shadow-focus":h,"--n-box-shadow-hover":_,"--n-caret-color":u,"--n-color":a,"--n-color-active":m,"--n-color-disabled":d,"--n-font-size":q,"--n-height":K,"--n-padding-single-top":J.top,"--n-padding-multiple-top":Y.top,"--n-padding-single-right":J.right,"--n-padding-multiple-right":Y.right,"--n-padding-single-left":J.left,"--n-padding-multiple-left":Y.left,"--n-padding-single-bottom":J.bottom,"--n-padding-multiple-bottom":Y.bottom,"--n-placeholder-color":o,"--n-placeholder-color-disabled":p,"--n-text-color":s,"--n-text-color-disabled":f,"--n-arrow-color":S,"--n-arrow-color-disabled":C,"--n-loading-color":T,"--n-color-active-warning":E,"--n-box-shadow-focus-warning":D,"--n-box-shadow-active-warning":O,"--n-box-shadow-hover-warning":k,"--n-border-warning":A,"--n-border-focus-warning":j,"--n-border-hover-warning":M,"--n-border-active-warning":N,"--n-color-active-error":P,"--n-box-shadow-focus-error":F,"--n-box-shadow-active-error":I,"--n-box-shadow-hover-error":L,"--n-border-error":z,"--n-border-focus-error":B,"--n-border-hover-error":V,"--n-border-active-error":H,"--n-clear-size":G,"--n-clear-color":U,"--n-clear-color-hover":W,"--n-clear-color-pressed":ee,"--n-arrow-size":te,"--n-font-weight":r}}),be=ve?Y(`internal-selection`,v(()=>t.size[0]),ye,t):void 0;return{mergedTheme:w,mergedClearable:T,mergedClsPrefix:n,rtlEnabled:a,patternInputFocused:S,filterablePlaceholder:E,label:O,selected:k,showTagsPanel:x,isComposing:K,counterRef:g,counterWrapperRef:_,patternInputMirrorRef:c,patternInputRef:l,selfRef:f,multipleElRef:p,singleElRef:m,patternInputWrapperRef:h,overflowRef:y,inputTagElRef:b,handleMouseDown:ee,handleFocusin:z,handleClear:V,handleMouseEnter:H,handleMouseLeave:W,handleDeleteOption:G,handlePatternKeyDown:q,handlePatternInputInput:re,handlePatternInputBlur:ae,handlePatternInputFocus:Z,handleMouseEnterCounter:he,handleMouseLeaveCounter:ge,handleFocusout:B,handleCompositionEnd:ie,handleCompositionStart:X,onPopoverUpdateShow:_e,focus:se,focusInput:ce,blur:oe,blurInput:le,updateCounter:ue,getCounter:de,getTail:fe,renderLabel:t.renderLabel,cssVars:ve?void 0:ye,themeClass:be?.themeClass,onRender:be?.onRender}},render(){let{status:e,multiple:t,size:n,disabled:r,filterable:i,maxTagCount:a,bordered:o,clsPrefix:s,ellipsisTagPopoverProps:c,onRender:u,renderTag:d,renderLabel:f}=this;u?.();let p=a===`responsive`,m=typeof a==`number`,g=p||m,_=l(z,null,{default:()=>l(Ee,{clsPrefix:s,loading:this.loading,showArrow:this.showArrow,showClear:this.mergedClearable&&this.selected,onClear:this.handleClear},{default:()=>{var e;return(e=this.$slots).arrow?.call(e)}})}),v;if(t){let{labelField:e}=this,t=t=>l(`div`,{class:`${s}-base-selection-tag-wrapper`,key:t.value},d?d({option:t,handleClose:()=>{this.handleDeleteOption(t)}}):l(xe,{size:n,closable:!t.disabled,disabled:r,onClose:()=>{this.handleDeleteOption(t)},internalCloseIsButtonTag:!1,internalCloseFocusable:!1},{default:()=>f?f(t,!0):Q(t[e],t,!0)})),o=()=>(m?this.selectedOptions.slice(0,a):this.selectedOptions).map(t),u=i?l(`div`,{class:`${s}-base-selection-input-tag`,ref:`inputTagElRef`,key:`__input-tag__`},l(`input`,Object.assign({},this.inputProps,{ref:`patternInputRef`,tabindex:-1,disabled:r,value:this.pattern,autofocus:this.autofocus,class:`${s}-base-selection-input-tag__input`,onBlur:this.handlePatternInputBlur,onFocus:this.handlePatternInputFocus,onKeydown:this.handlePatternKeyDown,onInput:this.handlePatternInputInput,onCompositionstart:this.handleCompositionStart,onCompositionend:this.handleCompositionEnd})),l(`span`,{ref:`patternInputMirrorRef`,class:`${s}-base-selection-input-tag__mirror`},this.pattern)):null,y=p?()=>l(`div`,{class:`${s}-base-selection-tag-wrapper`,ref:`counterWrapperRef`},l(xe,{size:n,ref:`counterRef`,onMouseenter:this.handleMouseEnterCounter,onMouseleave:this.handleMouseLeaveCounter,disabled:r})):void 0,b;if(m){let e=this.selectedOptions.length-a;e>0&&(b=l(`div`,{class:`${s}-base-selection-tag-wrapper`,key:`__counter__`},l(xe,{size:n,ref:`counterRef`,onMouseenter:this.handleMouseEnterCounter,disabled:r},{default:()=>`+${e}`})))}let x=p?i?l(ye,{ref:`overflowRef`,updateCounter:this.updateCounter,getCounter:this.getCounter,getTail:this.getTail,style:{width:`100%`,display:`flex`,overflow:`hidden`}},{default:o,counter:y,tail:()=>u}):l(ye,{ref:`overflowRef`,updateCounter:this.updateCounter,getCounter:this.getCounter,style:{width:`100%`,display:`flex`,overflow:`hidden`}},{default:o,counter:y}):m&&b?o().concat(b):o(),S=g?()=>l(`div`,{class:`${s}-base-selection-popover`},p?o():this.selectedOptions.map(t)):void 0,C=g?Object.assign({show:this.showTagsPanel,trigger:`hover`,overlap:!0,placement:`top`,width:`trigger`,onUpdateShow:this.onPopoverUpdateShow,theme:this.mergedTheme.peers.Popover,themeOverrides:this.mergedTheme.peerOverrides.Popover},c):null,w=!this.selected&&(!this.active||!this.pattern&&!this.isComposing)?l(`div`,{class:`${s}-base-selection-placeholder ${s}-base-selection-overlay`},l(`div`,{class:`${s}-base-selection-placeholder__inner`},this.placeholder)):null,T=i?l(`div`,{ref:`patternInputWrapperRef`,class:`${s}-base-selection-tags`},x,p?null:u,_):l(`div`,{ref:`multipleElRef`,class:`${s}-base-selection-tags`,tabindex:r?void 0:0},x,_);v=l(h,null,g?l(he,Object.assign({},C,{scrollable:!0,style:`max-height: calc(var(--v-target-height) * 6.6);`}),{trigger:()=>T,default:S}):T,w)}else if(i){let e=this.pattern||this.isComposing,t=this.active?!e:!this.selected,n=this.active?!1:this.selected;v=l(`div`,{ref:`patternInputWrapperRef`,class:`${s}-base-selection-label`,title:this.patternInputFocused?void 0:He(this.label)},l(`input`,Object.assign({},this.inputProps,{ref:`patternInputRef`,class:`${s}-base-selection-input`,value:this.active?this.pattern:``,placeholder:``,readonly:r,disabled:r,tabindex:-1,autofocus:this.autofocus,onFocus:this.handlePatternInputFocus,onBlur:this.handlePatternInputBlur,onInput:this.handlePatternInputInput,onCompositionstart:this.handleCompositionStart,onCompositionend:this.handleCompositionEnd})),n?l(`div`,{class:`${s}-base-selection-label__render-label ${s}-base-selection-overlay`,key:`input`},l(`div`,{class:`${s}-base-selection-overlay__wrapper`},d?d({option:this.selectedOption,handleClose:()=>{}}):f?f(this.selectedOption,!0):Q(this.label,this.selectedOption,!0))):null,t?l(`div`,{class:`${s}-base-selection-placeholder ${s}-base-selection-overlay`,key:`placeholder`},l(`div`,{class:`${s}-base-selection-overlay__wrapper`},this.filterablePlaceholder)):null,_)}else v=l(`div`,{ref:`singleElRef`,class:`${s}-base-selection-label`,tabindex:this.disabled?void 0:0},this.label===void 0?l(`div`,{class:`${s}-base-selection-placeholder ${s}-base-selection-overlay`,key:`placeholder`},l(`div`,{class:`${s}-base-selection-placeholder__inner`},this.placeholder)):l(`div`,{class:`${s}-base-selection-input`,title:He(this.label),key:`input`},l(`div`,{class:`${s}-base-selection-input__content`},d?d({option:this.selectedOption,handleClose:()=>{}}):f?f(this.selectedOption,!0):Q(this.label,this.selectedOption,!0))),_);return l(`div`,{ref:`selfRef`,class:[`${s}-base-selection`,this.rtlEnabled&&`${s}-base-selection--rtl`,this.themeClass,e&&`${s}-base-selection--${e}-status`,{[`${s}-base-selection--active`]:this.active,[`${s}-base-selection--selected`]:this.selected||this.active&&this.pattern,[`${s}-base-selection--disabled`]:this.disabled,[`${s}-base-selection--multiple`]:this.multiple,[`${s}-base-selection--focus`]:this.focused}],style:this.cssVars,onClick:this.onClick,onMouseenter:this.handleMouseEnter,onMouseleave:this.handleMouseLeave,onKeydown:this.onKeydown,onFocusin:this.handleFocusin,onFocusout:this.handleFocusout,onMousedown:this.handleMouseDown},v,o?l(`div`,{class:`${s}-base-selection__border`}):null,o?l(`div`,{class:`${s}-base-selection__state-border`}):null)}});function ft(e){return e.type===`group`}function pt(e){return e.type===`ignored`}function mt(e,t){try{return!!(1+t.toString().toLowerCase().indexOf(e.trim().toLowerCase()))}catch{return!1}}function ht(e,t){return{getIsGroup:ft,getIgnored:pt,getKey(t){return ft(t)?t.name||t.key||`key-required`:t[e]},getChildren(e){return e[t]}}}function gt(e,t,n,r){if(!t)return e;function i(e){if(!Array.isArray(e))return[];let a=[];for(let o of e)if(ft(o)){let e=i(o[r]);e.length&&a.push(Object.assign({},o,{[r]:e}))}else if(pt(o))continue;else t(n,o)&&a.push(o);return a}return i(e)}function _t(e,t,n){let r=new Map;return e.forEach(e=>{ft(e)?e[n].forEach(e=>{r.set(e[t],e)}):r.set(e[t],e)}),r}function vt(e){let{boxShadow2:t}=e;return{menuBoxShadow:t}}var yt=x({name:`Popselect`,common:q,peers:{Popover:le,InternalSelectMenu:tt},self:vt}),bt=A(`n-popselect`),xt=P(`popselect-menu`,`
 box-shadow: var(--n-menu-box-shadow);
`),St={multiple:Boolean,value:{type:[String,Number,Array],default:null},cancelable:Boolean,options:{type:Array,default:()=>[]},size:String,scrollable:Boolean,"onUpdate:value":[Function,Array],onUpdateValue:[Function,Array],onMouseenter:Function,onMouseleave:Function,renderLabel:Function,showCheckmark:{type:Boolean,default:void 0},nodeProps:Function,virtualScroll:Boolean,onChange:[Function,Array]},Ct=b(St),wt=n({name:`PopselectPanel`,props:St,setup(t){let n=m(bt),{mergedClsPrefixRef:r,inlineThemeDisabled:i,mergedComponentPropsRef:a}=te(t),o=v(()=>t.size||a?.value?.Popselect?.size||`medium`),c=D(`Popselect`,`-pop-select`,xt,yt,n.props,r),l=v(()=>be(t.options,ht(`value`,`children`)));function d(e,n){let{onUpdateValue:r,"onUpdate:value":i,onChange:a}=t;r&&S(r,e,n),i&&S(i,e,n),a&&S(a,e,n)}function f(e){h(e.key)}function p(e){!$(e,`action`)&&!$(e,`empty`)&&!$(e,`header`)&&e.preventDefault()}function h(e){let{value:{getNode:r}}=l;if(t.multiple)if(Array.isArray(t.value)){let n=[],i=[],a=!0;t.value.forEach(t=>{if(t===e){a=!1;return}let o=r(t);o&&(n.push(o.key),i.push(o.rawNode))}),a&&(n.push(e),i.push(r(e).rawNode)),d(n,i)}else{let t=r(e);t&&d([e],[t.rawNode])}else if(t.value===e&&t.cancelable)d(null,null);else{let t=r(e);t&&d(e,t.rawNode);let{"onUpdate:show":i,onUpdateShow:a}=n.props;i&&S(i,!1),a&&S(a,!1),n.setShow(!1)}s(()=>{n.syncPosition()})}u(e(t,`options`),()=>{s(()=>{n.syncPosition()})});let g=v(()=>{let{self:{menuBoxShadow:e}}=c.value;return{"--n-menu-box-shadow":e}}),_=i?Y(`select`,void 0,g,n.props):void 0;return{mergedTheme:n.mergedThemeRef,mergedClsPrefix:r,treeMate:l,handleToggle:f,handleMenuMousedown:p,cssVars:i?void 0:g,themeClass:_?.themeClass,onRender:_?.onRender,mergedSize:o,scrollbarProps:n.props.scrollbarProps}},render(){var e;return(e=this.onRender)==null||e.call(this),l(ot,{clsPrefix:this.mergedClsPrefix,focusable:!0,nodeProps:this.nodeProps,class:[`${this.mergedClsPrefix}-popselect-menu`,this.themeClass],style:this.cssVars,theme:this.mergedTheme.peers.InternalSelectMenu,themeOverrides:this.mergedTheme.peerOverrides.InternalSelectMenu,multiple:this.multiple,treeMate:this.treeMate,size:this.mergedSize,value:this.value,virtualScroll:this.virtualScroll,scrollable:this.scrollable,scrollbarProps:this.scrollbarProps,renderLabel:this.renderLabel,onToggle:this.handleToggle,onMouseenter:this.onMouseenter,onMouseleave:this.onMouseenter,onMousedown:this.handleMenuMousedown,showCheckmark:this.showCheckmark},{header:()=>{var e;return(e=this.$slots).header?.call(e)||[]},action:()=>{var e;return(e=this.$slots).action?.call(e)||[]},empty:()=>{var e;return(e=this.$slots).empty?.call(e)||[]}})}}),Tt=n({name:`Popselect`,props:Object.assign(Object.assign(Object.assign(Object.assign(Object.assign({},D.props),k(fe,[`showArrow`,`arrow`])),{placement:Object.assign(Object.assign({},fe.placement),{default:`bottom`}),trigger:{type:String,default:`hover`}}),St),{scrollbarProps:Object}),slots:Object,inheritAttrs:!1,__popover__:!0,setup(e){let{mergedClsPrefixRef:n}=te(e),r=D(`Popselect`,`-popselect`,void 0,yt,e,n),i=d(null);function a(){var e;(e=i.value)==null||e.syncPosition()}function o(e){var t;(t=i.value)==null||t.setShow(e)}return t(bt,{props:e,mergedThemeRef:r,syncPosition:a,setShow:o}),Object.assign(Object.assign({},{syncPosition:a,setShow:o}),{popoverInstRef:i,mergedTheme:r})},render(){let{mergedTheme:e}=this,t={theme:e.peers.Popover,themeOverrides:e.peerOverrides.Popover,builtinThemeOverrides:{padding:`0`},ref:`popoverInstRef`,internalRenderBody:(e,t,n,r,i)=>{let{$attrs:a}=this;return l(wt,Object.assign({},a,{class:[a.class,e],style:[a.style,...n]},Z(this.$props,Ct),{ref:_e(t),onMouseenter:Ge([r,a.onMouseenter]),onMouseleave:Ge([i,a.onMouseleave])}),{header:()=>{var e;return(e=this.$slots).header?.call(e)},action:()=>{var e;return(e=this.$slots).action?.call(e)},empty:()=>{var e;return(e=this.$slots).empty?.call(e)}})}};return l(he,Object.assign({},k(this.$props,Ct),t,{internalDeactivateImmediately:!0}),{trigger:()=>{var e;return(e=this.$slots).default?.call(e)}})}});function Et(e){let{boxShadow2:t}=e;return{menuBoxShadow:t}}var Dt=x({name:`Select`,common:q,peers:{InternalSelection:lt,InternalSelectMenu:tt},self:Et}),Ot=X([P(`select`,`
 z-index: auto;
 outline: none;
 width: 100%;
 position: relative;
 font-weight: var(--n-font-weight);
 `),P(`select-menu`,`
 margin: 4px 0;
 box-shadow: var(--n-menu-box-shadow);
 `,[W({originalTransition:`background-color .3s var(--n-bezier), box-shadow .3s var(--n-bezier)`})])]),kt=n({name:`Select`,props:Object.assign(Object.assign({},D.props),{to:se.propTo,bordered:{type:Boolean,default:void 0},clearable:Boolean,clearCreatedOptionsOnClear:{type:Boolean,default:!0},clearFilterAfterSelect:{type:Boolean,default:!0},options:{type:Array,default:()=>[]},defaultValue:{type:[String,Number,Array],default:null},keyboard:{type:Boolean,default:!0},value:[String,Number,Array],placeholder:String,menuProps:Object,multiple:Boolean,size:String,menuSize:{type:String},filterable:Boolean,disabled:{type:Boolean,default:void 0},remote:Boolean,loading:Boolean,filter:Function,placement:{type:String,default:`bottom-start`},widthMode:{type:String,default:`trigger`},tag:Boolean,onCreate:Function,fallbackOption:{type:[Function,Boolean],default:void 0},show:{type:Boolean,default:void 0},showArrow:{type:Boolean,default:!0},maxTagCount:[Number,String],ellipsisTagPopoverProps:Object,consistentMenuWidth:{type:Boolean,default:!0},virtualScroll:{type:Boolean,default:!0},labelField:{type:String,default:`label`},valueField:{type:String,default:`value`},childrenField:{type:String,default:`children`},renderLabel:Function,renderOption:Function,renderTag:Function,"onUpdate:value":[Function,Array],inputProps:Object,nodeProps:Function,ignoreComposition:{type:Boolean,default:!0},showOnFocus:Boolean,onUpdateValue:[Function,Array],onBlur:[Function,Array],onClear:[Function,Array],onFocus:[Function,Array],onScroll:[Function,Array],onSearch:[Function,Array],onUpdateShow:[Function,Array],"onUpdate:show":[Function,Array],displayDirective:{type:String,default:`show`},resetMenuOnOptionsChange:{type:Boolean,default:!0},status:String,showCheckmark:{type:Boolean,default:!0},scrollbarProps:Object,onChange:[Function,Array],items:Array}),slots:Object,setup(t){let{mergedClsPrefixRef:n,mergedBorderedRef:r,namespaceRef:i,inlineThemeDisabled:a,mergedComponentPropsRef:o}=te(t),s=D(`Select`,`-select`,Ot,Dt,t,n),c=d(t.defaultValue),l=Se(e(t,`value`),c),f=d(!1),p=d(``),m=Ce(t,[`items`,`options`]),h=d([]),g=d([]),_=v(()=>g.value.concat(h.value).concat(m.value)),y=v(()=>{let{filter:e}=t;if(e)return e;let{labelField:n,valueField:r}=t;return(e,t)=>{if(!t)return!1;let i=t[n];if(typeof i==`string`)return mt(e,i);let a=t[r];return typeof a==`string`?mt(e,a):typeof a==`number`?mt(e,String(a)):!1}}),b=v(()=>{if(t.remote)return m.value;{let{value:e}=_,{value:n}=p;return!n.length||!t.filterable?e:gt(e,y.value,n,t.childrenField)}}),x=v(()=>{let{valueField:e,childrenField:n}=t,r=ht(e,n);return be(b.value,r)}),C=v(()=>_t(_.value,t.valueField,t.childrenField)),w=d(!1),T=Se(e(t,`show`),w),O=d(null),k=d(null),A=d(null),{localeRef:M}=we(`Select`),N=v(()=>t.placeholder??M.value.placeholder),P=[],F=d(new Map),I=v(()=>{let{fallbackOption:e}=t;if(e===void 0){let{labelField:e,valueField:n}=t;return t=>({[e]:String(t),[n]:t})}return e===!1?!1:t=>Object.assign(e(t),{value:t})});function R(e){let n=t.remote,{value:r}=F,{value:i}=C,{value:a}=I,o=[];return e.forEach(e=>{if(i.has(e))o.push(i.get(e));else if(n&&r.has(e))o.push(r.get(e));else if(a){let t=a(e);t&&o.push(t)}}),o}let z=v(()=>{if(t.multiple){let{value:e}=l;return Array.isArray(e)?R(e):[]}return null}),B=v(()=>{let{value:e}=l;return!t.multiple&&!Array.isArray(e)?e===null?null:R([e])[0]||null:null}),V=L(t,{mergedSize:e=>{let{size:n}=t;if(n)return n;let{mergedSize:r}=e||{};return r?.value?r.value:o?.value?.Select?.size||`medium`}}),{mergedSizeRef:H,mergedDisabledRef:U,mergedStatusRef:W}=V;function G(e,n){let{onChange:r,"onUpdate:value":i,onUpdateValue:a}=t,{nTriggerFormChange:o,nTriggerFormInput:s}=V;r&&S(r,e,n),a&&S(a,e,n),i&&S(i,e,n),c.value=e,o(),s()}function K(e){let{onBlur:n}=t,{nTriggerFormBlur:r}=V;n&&S(n,e),r()}function q(){let{onClear:e}=t;e&&S(e)}function J(e){let{onFocus:n,showOnFocus:r}=t,{nTriggerFormFocus:i}=V;n&&S(n,e),i(),r&&Z()}function ne(e){let{onSearch:n}=t;n&&S(n,e)}function re(e){let{onScroll:n}=t;n&&S(n,e)}function X(){var e;let{remote:n,multiple:r}=t;if(n){let{value:n}=F;if(r){let{valueField:r}=t;(e=z.value)==null||e.forEach(e=>{n.set(e[r],e)})}else{let e=B.value;e&&n.set(e[t.valueField],e)}}}function ie(e){let{onUpdateShow:n,"onUpdate:show":r}=t;n&&S(n,e),r&&S(r,e),w.value=e}function Z(){U.value||(ie(!0),w.value=!0,t.filterable&&je())}function Q(){ie(!1)}function ae(){p.value=``,g.value=P}let oe=d(!1);function ce(){t.filterable&&(oe.value=!0)}function le(){t.filterable&&(oe.value=!1,T.value||ae())}function ue(){U.value||(T.value?t.filterable?je():Q():Z())}function de(e){(A.value?.selfRef)?.contains(e.relatedTarget)||(f.value=!1,K(e),Q())}function fe(e){J(e),f.value=!0}function pe(){f.value=!0}function me(e){O.value?.$el.contains(e.relatedTarget)||(f.value=!1,K(e),Q())}function he(){var e;(e=O.value)==null||e.focus(),Q()}function ge(e){T.value&&(O.value?.$el.contains(ee(e))||Q())}function _e(e){if(!Array.isArray(e))return[];if(I.value)return Array.from(e);{let{remote:n}=t,{value:r}=C;if(n){let{value:t}=F;return e.filter(e=>r.has(e)||t.has(e))}else return e.filter(e=>r.has(e))}}function ve(e){ye(e.rawNode)}function ye(e){if(U.value)return;let{tag:n,remote:r,clearFilterAfterSelect:i,valueField:a}=t;if(n&&!r){let{value:e}=g,t=e[0]||null;if(t){let e=h.value;e.length?e.push(t):h.value=[t],g.value=P}}if(r&&F.value.set(e[a],e),t.multiple){let t=_e(l.value),o=t.findIndex(t=>t===e[a]);if(~o){if(t.splice(o,1),n&&!r){let t=xe(e[a]);~t&&(h.value.splice(t,1),i&&(p.value=``))}}else t.push(e[a]),i&&(p.value=``);G(t,R(t))}else{if(n&&!r){let t=xe(e[a]);~t?h.value=[h.value[t]]:h.value=P}Ae(),Q(),G(e[a],e)}}function xe(e){return h.value.findIndex(n=>n[t.valueField]===e)}function Te(e){T.value||Z();let{value:n}=e.target;p.value=n;let{tag:r,remote:i}=t;if(ne(n),r&&!i){if(!n){g.value=P;return}let{onCreate:e}=t,r=e?e(n):{[t.labelField]:n,[t.valueField]:n},{valueField:i,labelField:a}=t;m.value.some(e=>e[i]===r[i]||e[a]===r[a])||h.value.some(e=>e[i]===r[i]||e[a]===r[a])?g.value=P:g.value=[r]}}function Ee(e){e.stopPropagation();let{multiple:n,tag:r,remote:i,clearCreatedOptionsOnClear:a}=t;!n&&t.filterable&&Q(),r&&!i&&a&&(h.value=P),q(),n?G([],[]):G(null,null)}function De(e){!$(e,`action`)&&!$(e,`empty`)&&!$(e,`header`)&&e.preventDefault()}function Oe(e){re(e)}function ke(e){var n,r,i;if(!t.keyboard){e.preventDefault();return}switch(e.key){case` `:if(t.filterable)break;e.preventDefault();case`Enter`:if(!O.value?.isComposing){if(T.value){let e=A.value?.getPendingTmNode();e?ve(e):t.filterable||(Q(),Ae())}else if(Z(),t.tag&&oe.value){let e=g.value[0];if(e){let n=e[t.valueField],{value:r}=l;t.multiple&&Array.isArray(r)&&r.includes(n)||ye(e)}}}e.preventDefault();break;case`ArrowUp`:if(e.preventDefault(),t.loading)return;T.value&&((n=A.value)==null||n.prev());break;case`ArrowDown`:if(e.preventDefault(),t.loading)return;T.value?(r=A.value)==null||r.next():Z();break;case`Escape`:T.value&&(E(e),Q()),(i=O.value)==null||i.focus();break}}function Ae(){var e;(e=O.value)==null||e.focus()}function je(){var e;(e=O.value)==null||e.focusInput()}function Me(){var e;T.value&&((e=k.value)==null||e.syncPosition())}X(),u(e(t,`options`),X);let Ne={focus:()=>{var e;(e=O.value)==null||e.focus()},focusInput:()=>{var e;(e=O.value)==null||e.focusInput()},blur:()=>{var e;(e=O.value)==null||e.blur()},blurInput:()=>{var e;(e=O.value)==null||e.blurInput()}},Pe=v(()=>{let{self:{menuBoxShadow:e}}=s.value;return{"--n-menu-box-shadow":e}}),Fe=a?Y(`select`,void 0,Pe,t):void 0;return Object.assign(Object.assign({},Ne),{mergedStatus:W,mergedClsPrefix:n,mergedBordered:r,namespace:i,treeMate:x,isMounted:j(),triggerRef:O,menuRef:A,pattern:p,uncontrolledShow:w,mergedShow:T,adjustedTo:se(t),uncontrolledValue:c,mergedValue:l,followerRef:k,localizedPlaceholder:N,selectedOption:B,selectedOptions:z,mergedSize:H,mergedDisabled:U,focused:f,activeWithoutMenuOpen:oe,inlineThemeDisabled:a,onTriggerInputFocus:ce,onTriggerInputBlur:le,handleTriggerOrMenuResize:Me,handleMenuFocus:pe,handleMenuBlur:me,handleMenuTabOut:he,handleTriggerClick:ue,handleToggle:ve,handleDeleteOption:ye,handlePatternInput:Te,handleClear:Ee,handleTriggerBlur:de,handleTriggerFocus:fe,handleKeydown:ke,handleMenuAfterLeave:ae,handleMenuClickOutside:ge,handleMenuScroll:Oe,handleMenuKeydown:ke,handleMenuMousedown:De,mergedTheme:s,cssVars:a?void 0:Pe,themeClass:Fe?.themeClass,onRender:Fe?.onRender})},render(){return l(`div`,{class:`${this.mergedClsPrefix}-select`},l(oe,null,{default:()=>[l(ge,null,{default:()=>l(dt,{ref:`triggerRef`,inlineThemeDisabled:this.inlineThemeDisabled,status:this.mergedStatus,inputProps:this.inputProps,clsPrefix:this.mergedClsPrefix,showArrow:this.showArrow,maxTagCount:this.maxTagCount,ellipsisTagPopoverProps:this.ellipsisTagPopoverProps,bordered:this.mergedBordered,active:this.activeWithoutMenuOpen||this.mergedShow,pattern:this.pattern,placeholder:this.localizedPlaceholder,selectedOption:this.selectedOption,selectedOptions:this.selectedOptions,multiple:this.multiple,renderTag:this.renderTag,renderLabel:this.renderLabel,filterable:this.filterable,clearable:this.clearable,disabled:this.mergedDisabled,size:this.mergedSize,theme:this.mergedTheme.peers.InternalSelection,labelField:this.labelField,valueField:this.valueField,themeOverrides:this.mergedTheme.peerOverrides.InternalSelection,loading:this.loading,focused:this.focused,onClick:this.handleTriggerClick,onDeleteOption:this.handleDeleteOption,onPatternInput:this.handlePatternInput,onClear:this.handleClear,onBlur:this.handleTriggerBlur,onFocus:this.handleTriggerFocus,onKeydown:this.handleKeydown,onPatternBlur:this.onTriggerInputBlur,onPatternFocus:this.onTriggerInputFocus,onResize:this.handleTriggerOrMenuResize,ignoreComposition:this.ignoreComposition},{arrow:()=>{var e;return[(e=this.$slots).arrow?.call(e)]}})}),l(me,{ref:`followerRef`,show:this.mergedShow,to:this.adjustedTo,teleportDisabled:this.adjustedTo===se.tdkey,containerClass:this.namespace,width:this.consistentMenuWidth?`target`:void 0,minWidth:`target`,placement:this.placement},{default:()=>l(_,{name:`fade-in-scale-up-transition`,appear:this.isMounted,onAfterLeave:this.handleMenuAfterLeave},{default:()=>{var e;return this.mergedShow||this.displayDirective===`show`?((e=this.onRender)==null||e.call(this),g(l(ot,Object.assign({},this.menuProps,{ref:`menuRef`,onResize:this.handleTriggerOrMenuResize,inlineThemeDisabled:this.inlineThemeDisabled,virtualScroll:this.consistentMenuWidth&&this.virtualScroll,class:[`${this.mergedClsPrefix}-select-menu`,this.themeClass,this.menuProps?.class],clsPrefix:this.mergedClsPrefix,focusable:!0,labelField:this.labelField,valueField:this.valueField,autoPending:!0,nodeProps:this.nodeProps,theme:this.mergedTheme.peers.InternalSelectMenu,themeOverrides:this.mergedTheme.peerOverrides.InternalSelectMenu,treeMate:this.treeMate,multiple:this.multiple,size:this.menuSize,renderOption:this.renderOption,renderLabel:this.renderLabel,value:this.mergedValue,style:[this.menuProps?.style,this.cssVars],onToggle:this.handleToggle,onScroll:this.handleMenuScroll,onFocus:this.handleMenuFocus,onBlur:this.handleMenuBlur,onKeydown:this.handleMenuKeydown,onTabOut:this.handleMenuTabOut,onMousedown:this.handleMenuMousedown,show:this.mergedShow,showCheckmark:this.showCheckmark,resetMenuOnOptionsChange:this.resetMenuOnOptionsChange,scrollbarProps:this.scrollbarProps}),{empty:()=>{var e;return[(e=this.$slots).empty?.call(e)]},header:()=>{var e;return[(e=this.$slots).header?.call(e)]},action:()=>{var e;return[(e=this.$slots).action?.call(e)]}}),this.displayDirective===`show`?[[f,this.mergedShow],[y,this.handleMenuClickOutside,void 0,{capture:!0}]]:[[y,this.handleMenuClickOutside,void 0,{capture:!0}]])):null}})})]}))}}),At={itemPaddingSmall:`0 4px`,itemMarginSmall:`0 0 0 8px`,itemMarginSmallRtl:`0 8px 0 0`,itemPaddingMedium:`0 4px`,itemMarginMedium:`0 0 0 8px`,itemMarginMediumRtl:`0 8px 0 0`,itemPaddingLarge:`0 4px`,itemMarginLarge:`0 0 0 8px`,itemMarginLargeRtl:`0 8px 0 0`,buttonIconSizeSmall:`14px`,buttonIconSizeMedium:`16px`,buttonIconSizeLarge:`18px`,inputWidthSmall:`60px`,selectWidthSmall:`unset`,inputMarginSmall:`0 0 0 8px`,inputMarginSmallRtl:`0 8px 0 0`,selectMarginSmall:`0 0 0 8px`,prefixMarginSmall:`0 8px 0 0`,suffixMarginSmall:`0 0 0 8px`,inputWidthMedium:`60px`,selectWidthMedium:`unset`,inputMarginMedium:`0 0 0 8px`,inputMarginMediumRtl:`0 8px 0 0`,selectMarginMedium:`0 0 0 8px`,prefixMarginMedium:`0 8px 0 0`,suffixMarginMedium:`0 0 0 8px`,inputWidthLarge:`60px`,selectWidthLarge:`unset`,inputMarginLarge:`0 0 0 8px`,inputMarginLargeRtl:`0 8px 0 0`,selectMarginLarge:`0 0 0 8px`,prefixMarginLarge:`0 8px 0 0`,suffixMarginLarge:`0 0 0 8px`};function jt(e){let{textColor2:t,primaryColor:n,primaryColorHover:r,primaryColorPressed:i,inputColorDisabled:a,textColorDisabled:o,borderColor:s,borderRadius:c,fontSizeTiny:l,fontSizeSmall:u,fontSizeMedium:d,heightTiny:f,heightSmall:p,heightMedium:m}=e;return Object.assign(Object.assign({},At),{buttonColor:`#0000`,buttonColorHover:`#0000`,buttonColorPressed:`#0000`,buttonBorder:`1px solid ${s}`,buttonBorderHover:`1px solid ${s}`,buttonBorderPressed:`1px solid ${s}`,buttonIconColor:t,buttonIconColorHover:t,buttonIconColorPressed:t,itemTextColor:t,itemTextColorHover:r,itemTextColorPressed:i,itemTextColorActive:n,itemTextColorDisabled:o,itemColor:`#0000`,itemColorHover:`#0000`,itemColorPressed:`#0000`,itemColorActive:`#0000`,itemColorActiveHover:`#0000`,itemColorDisabled:a,itemBorder:`1px solid #0000`,itemBorderHover:`1px solid #0000`,itemBorderPressed:`1px solid #0000`,itemBorderActive:`1px solid ${n}`,itemBorderDisabled:`1px solid ${s}`,itemBorderRadius:c,itemSizeSmall:f,itemSizeMedium:p,itemSizeLarge:m,itemFontSizeSmall:l,itemFontSizeMedium:u,itemFontSizeLarge:d,jumperFontSizeSmall:l,jumperFontSizeMedium:u,jumperFontSizeLarge:d,jumperTextColor:t,jumperTextColorDisabled:o})}var Mt=x({name:`Pagination`,common:q,peers:{Select:Dt,Input:Te,Popselect:yt},self:jt}),Nt=`
 background: var(--n-item-color-hover);
 color: var(--n-item-text-color-hover);
 border: var(--n-item-border-hover);
`,Pt=[G(`button`,`
 background: var(--n-button-color-hover);
 border: var(--n-button-border-hover);
 color: var(--n-button-icon-color-hover);
 `)],Ft=P(`pagination`,`
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
 `),X(`> *:not(:first-child)`,`
 margin: var(--n-item-margin);
 `),P(`select`,`
 width: var(--n-select-width);
 `),X(`&.transition-disabled`,[P(`pagination-item`,`transition: none!important;`)]),P(`pagination-quick-jumper`,`
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
 `)]),V(`disabled`,[G(`hover`,Nt,Pt),X(`&:hover`,Nt,Pt),X(`&:active`,`
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
 `,[X(`&:hover`,`
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
 `)])])]);function It(e){if(!e)return 10;let{defaultPageSize:t}=e;if(t!==void 0)return t;let n=e.pageSizes?.[0];return typeof n==`number`?n:n?.value||10}function Lt(e,t,n,r){let i=!1,a=!1,o=1,s=t;if(t===1)return{hasFastBackward:!1,hasFastForward:!1,fastForwardTo:s,fastBackwardTo:o,items:[{type:`page`,label:1,active:e===1,mayBeFastBackward:!1,mayBeFastForward:!1}]};if(t===2)return{hasFastBackward:!1,hasFastForward:!1,fastForwardTo:s,fastBackwardTo:o,items:[{type:`page`,label:1,active:e===1,mayBeFastBackward:!1,mayBeFastForward:!1},{type:`page`,label:2,active:e===2,mayBeFastBackward:!0,mayBeFastForward:!1}]};let c=t,l=e,u=e,d=(n-5)/2;u+=Math.ceil(d),u=Math.min(Math.max(u,1+n-3),c-2),l-=Math.floor(d),l=Math.max(Math.min(l,c-n+3),3);let f=!1,p=!1;l>3&&(f=!0),u<c-2&&(p=!0);let m=[];m.push({type:`page`,label:1,active:e===1,mayBeFastBackward:!1,mayBeFastForward:!1}),f?(i=!0,o=l-1,m.push({type:`fast-backward`,active:!1,label:void 0,options:r?Rt(2,l-1):null})):c>=2&&m.push({type:`page`,label:2,mayBeFastBackward:!0,mayBeFastForward:!1,active:e===2});for(let t=l;t<=u;++t)m.push({type:`page`,label:t,mayBeFastBackward:!1,mayBeFastForward:!1,active:e===t});return p?(a=!0,s=u+1,m.push({type:`fast-forward`,active:!1,label:void 0,options:r?Rt(u+1,c-1):null})):u===c-2&&m[m.length-1].label!==c-1&&m.push({type:`page`,mayBeFastForward:!0,mayBeFastBackward:!1,label:c-1,active:e===c-1}),m[m.length-1].label!==c&&m.push({type:`page`,mayBeFastForward:!1,mayBeFastBackward:!1,label:c,active:e===c}),{hasFastBackward:i,hasFastForward:a,fastBackwardTo:o,fastForwardTo:s,items:m}}function Rt(e,t){let n=[];for(let r=e;r<=t;++r)n.push({label:`${r}`,value:r});return n}var zt=n({name:`Pagination`,props:Object.assign(Object.assign({},D.props),{simple:Boolean,page:Number,defaultPage:{type:Number,default:1},itemCount:Number,pageCount:Number,defaultPageCount:{type:Number,default:1},showSizePicker:Boolean,pageSize:Number,defaultPageSize:Number,pageSizes:{type:Array,default(){return[10]}},showQuickJumper:Boolean,size:String,disabled:Boolean,pageSlot:{type:Number,default:9},selectProps:Object,prev:Function,next:Function,goto:Function,prefix:Function,suffix:Function,label:Function,displayOrder:{type:Array,default:[`pages`,`size-picker`,`quick-jumper`]},to:se.propTo,showQuickJumpDropdown:{type:Boolean,default:!0},scrollbarProps:Object,"onUpdate:page":[Function,Array],onUpdatePage:[Function,Array],"onUpdate:pageSize":[Function,Array],onUpdatePageSize:[Function,Array],onPageSizeChange:[Function,Array],onChange:[Function,Array]}),slots:Object,setup(t){let{mergedComponentPropsRef:n,mergedClsPrefixRef:r,inlineThemeDisabled:a,mergedRtlRef:o}=te(t),c=v(()=>t.size||n?.value?.Pagination?.size||`medium`),l=D(`Pagination`,`-pagination`,Ft,Mt,t,r),{localeRef:u}=we(`Pagination`),f=d(null),p=d(t.defaultPage),m=d(It(t)),h=Se(e(t,`page`),p),g=Se(e(t,`pageSize`),m),_=v(()=>{let{itemCount:e}=t;if(e!==void 0)return Math.max(1,Math.ceil(e/g.value));let{pageCount:n}=t;return n===void 0?1:Math.max(n,1)}),y=d(``);i(()=>{t.simple,y.value=String(h.value)});let b=d(!1),x=d(!1),C=d(!1),w=d(!1),T=()=>{t.disabled||(b.value=!0,B())},E=()=>{t.disabled||(b.value=!1,B())},O=()=>{x.value=!0,B()},k=()=>{x.value=!1,B()},A=e=>{V(e)},j=v(()=>Lt(h.value,_.value,t.pageSlot,t.showQuickJumpDropdown));i(()=>{j.value.hasFastBackward?j.value.hasFastForward||(b.value=!1,C.value=!1):(x.value=!1,w.value=!1)});let M=v(()=>{let e=u.value.selectionSuffix;return t.pageSizes.map(t=>typeof t==`number`?{label:`${t} / ${e}`,value:t}:t)}),N=v(()=>n?.value?.Pagination?.inputSize||We(c.value)),P=v(()=>n?.value?.Pagination?.selectSize||We(c.value)),F=v(()=>(h.value-1)*g.value),I=v(()=>{let e=h.value*g.value-1,{itemCount:n}=t;return n===void 0?e:e>n-1?n-1:e}),L=v(()=>{let{itemCount:e}=t;return e===void 0?(t.pageCount||1)*g.value:e}),z=U(`Pagination`,o,r);function B(){s(()=>{var e;let{value:t}=f;t&&(t.classList.add(`transition-disabled`),(e=f.value)==null||e.offsetWidth,t.classList.remove(`transition-disabled`))})}function V(e){if(e===h.value)return;let{"onUpdate:page":n,onUpdatePage:r,onChange:i,simple:a}=t;n&&S(n,e),r&&S(r,e),i&&S(i,e),p.value=e,a&&(y.value=String(e))}function H(e){if(e===g.value)return;let{"onUpdate:pageSize":n,onUpdatePageSize:r,onPageSizeChange:i}=t;n&&S(n,e),r&&S(r,e),i&&S(i,e),m.value=e,_.value<h.value&&V(_.value)}function W(){t.disabled||V(Math.min(h.value+1,_.value))}function ee(){t.disabled||V(Math.max(h.value-1,1))}function G(){t.disabled||V(Math.min(j.value.fastForwardTo,_.value))}function K(){t.disabled||V(Math.max(j.value.fastBackwardTo,1))}function q(e){H(e)}function J(){let e=Number.parseInt(y.value);Number.isNaN(e)||(V(Math.max(1,Math.min(e,_.value))),t.simple||(y.value=``))}function ne(){J()}function re(e){if(!t.disabled)switch(e.type){case`page`:V(e.label);break;case`fast-backward`:K();break;case`fast-forward`:G();break}}function X(e){y.value=e.replace(/\D+/g,``)}i(()=>{h.value,g.value,B()});let ie=v(()=>{let e=c.value,{self:{buttonBorder:t,buttonBorderHover:n,buttonBorderPressed:r,buttonIconColor:i,buttonIconColorHover:a,buttonIconColorPressed:o,itemTextColor:s,itemTextColorHover:u,itemTextColorPressed:d,itemTextColorActive:f,itemTextColorDisabled:p,itemColor:m,itemColorHover:h,itemColorPressed:g,itemColorActive:_,itemColorActiveHover:v,itemColorDisabled:y,itemBorder:b,itemBorderHover:x,itemBorderPressed:S,itemBorderActive:C,itemBorderDisabled:w,itemBorderRadius:T,jumperTextColor:E,jumperTextColorDisabled:D,buttonColor:O,buttonColorHover:k,buttonColorPressed:A,[R(`itemPadding`,e)]:j,[R(`itemMargin`,e)]:M,[R(`inputWidth`,e)]:N,[R(`selectWidth`,e)]:P,[R(`inputMargin`,e)]:F,[R(`selectMargin`,e)]:I,[R(`jumperFontSize`,e)]:L,[R(`prefixMargin`,e)]:z,[R(`suffixMargin`,e)]:B,[R(`itemSize`,e)]:V,[R(`buttonIconSize`,e)]:H,[R(`itemFontSize`,e)]:U,[`${R(`itemMargin`,e)}Rtl`]:W,[`${R(`inputMargin`,e)}Rtl`]:ee},common:{cubicBezierEaseInOut:G}}=l.value;return{"--n-prefix-margin":z,"--n-suffix-margin":B,"--n-item-font-size":U,"--n-select-width":P,"--n-select-margin":I,"--n-input-width":N,"--n-input-margin":F,"--n-input-margin-rtl":ee,"--n-item-size":V,"--n-item-text-color":s,"--n-item-text-color-disabled":p,"--n-item-text-color-hover":u,"--n-item-text-color-active":f,"--n-item-text-color-pressed":d,"--n-item-color":m,"--n-item-color-hover":h,"--n-item-color-disabled":y,"--n-item-color-active":_,"--n-item-color-active-hover":v,"--n-item-color-pressed":g,"--n-item-border":b,"--n-item-border-hover":x,"--n-item-border-disabled":w,"--n-item-border-active":C,"--n-item-border-pressed":S,"--n-item-padding":j,"--n-item-border-radius":T,"--n-bezier":G,"--n-jumper-font-size":L,"--n-jumper-text-color":E,"--n-jumper-text-color-disabled":D,"--n-item-margin":M,"--n-item-margin-rtl":W,"--n-button-icon-size":H,"--n-button-icon-color":i,"--n-button-icon-color-hover":a,"--n-button-icon-color-pressed":o,"--n-button-color-hover":k,"--n-button-color":O,"--n-button-color-pressed":A,"--n-button-border":t,"--n-button-border-hover":n,"--n-button-border-pressed":r}}),Z=a?Y(`pagination`,v(()=>{let e=``;return e+=c.value[0],e}),ie,t):void 0;return{rtlEnabled:z,mergedClsPrefix:r,locale:u,selfRef:f,mergedPage:h,pageItems:v(()=>j.value.items),mergedItemCount:L,jumperValue:y,pageSizeOptions:M,mergedPageSize:g,inputSize:N,selectSize:P,mergedTheme:l,mergedPageCount:_,startIndex:F,endIndex:I,showFastForwardMenu:C,showFastBackwardMenu:w,fastForwardActive:b,fastBackwardActive:x,handleMenuSelect:A,handleFastForwardMouseenter:T,handleFastForwardMouseleave:E,handleFastBackwardMouseenter:O,handleFastBackwardMouseleave:k,handleJumperInput:X,handleBackwardClick:ee,handleForwardClick:W,handlePageItemClick:re,handleSizePickerChange:q,handleQuickJumperChange:ne,cssVars:a?void 0:ie,themeClass:Z?.themeClass,onRender:Z?.onRender}},render(){let{$slots:e,mergedClsPrefix:t,disabled:n,cssVars:r,mergedPage:i,mergedPageCount:a,pageItems:o,showSizePicker:s,showQuickJumper:c,mergedTheme:u,locale:d,inputSize:f,selectSize:p,mergedPageSize:m,pageSizeOptions:g,jumperValue:_,simple:v,prev:y,next:b,prefix:x,suffix:S,label:w,goto:T,handleJumperInput:E,handleSizePickerChange:D,handleBackwardClick:O,handlePageItemClick:k,handleForwardClick:A,handleQuickJumperChange:j,onRender:M}=this;M?.();let N=x||e.prefix,P=S||e.suffix,F=y||e.prev,I=b||e.next,L=w||e.label;return l(`div`,{ref:`selfRef`,class:[`${t}-pagination`,this.themeClass,this.rtlEnabled&&`${t}-pagination--rtl`,n&&`${t}-pagination--disabled`,v&&`${t}-pagination--simple`],style:r},N?l(`div`,{class:`${t}-pagination-prefix`},N({page:i,pageSize:m,pageCount:a,startIndex:this.startIndex,endIndex:this.endIndex,itemCount:this.mergedItemCount})):null,this.displayOrder.map(e=>{switch(e){case`pages`:return l(h,null,l(`div`,{class:[`${t}-pagination-item`,!F&&`${t}-pagination-item--button`,(i<=1||i>a||n)&&`${t}-pagination-item--disabled`],onClick:O},F?F({page:i,pageSize:m,pageCount:a,startIndex:this.startIndex,endIndex:this.endIndex,itemCount:this.mergedItemCount}):l(C,{clsPrefix:t},{default:()=>this.rtlEnabled?l(Xe,null):l(Ke,null)})),v?l(h,null,l(`div`,{class:`${t}-pagination-quick-jumper`},l(De,{value:_,onUpdateValue:E,size:f,placeholder:``,disabled:n,theme:u.peers.Input,themeOverrides:u.peerOverrides.Input,onChange:j})),`\xA0/`,` `,a):o.map((e,r)=>{let i,a,o,{type:s}=e;switch(s){case`page`:let n=e.label;i=L?L({type:`page`,node:n,active:e.active}):n;break;case`fast-forward`:let r=this.fastForwardActive?l(C,{clsPrefix:t},{default:()=>this.rtlEnabled?l(Je,null):l(Ye,null)}):l(C,{clsPrefix:t},{default:()=>l(Ze,null)});i=L?L({type:`fast-forward`,node:r,active:this.fastForwardActive||this.showFastForwardMenu}):r,a=this.handleFastForwardMouseenter,o=this.handleFastForwardMouseleave;break;case`fast-backward`:let s=this.fastBackwardActive?l(C,{clsPrefix:t},{default:()=>this.rtlEnabled?l(Ye,null):l(Je,null)}):l(C,{clsPrefix:t},{default:()=>l(Ze,null)});i=L?L({type:`fast-backward`,node:s,active:this.fastBackwardActive||this.showFastBackwardMenu}):s,a=this.handleFastBackwardMouseenter,o=this.handleFastBackwardMouseleave;break}let c=l(`div`,{key:r,class:[`${t}-pagination-item`,e.active&&`${t}-pagination-item--active`,s!==`page`&&(s===`fast-backward`&&this.showFastBackwardMenu||s===`fast-forward`&&this.showFastForwardMenu)&&`${t}-pagination-item--hover`,n&&`${t}-pagination-item--disabled`,s===`page`&&`${t}-pagination-item--clickable`],onClick:()=>{k(e)},onMouseenter:a,onMouseleave:o},i);if(s===`page`&&!e.mayBeFastBackward&&!e.mayBeFastForward)return c;{let t=e.type===`page`?e.mayBeFastBackward?`fast-backward`:`fast-forward`:e.type;return e.type!==`page`&&!e.options?c:l(Tt,{to:this.to,key:t,disabled:n,trigger:`hover`,virtualScroll:!0,style:{width:`60px`},theme:u.peers.Popselect,themeOverrides:u.peerOverrides.Popselect,builtinThemeOverrides:{peers:{InternalSelectMenu:{height:`calc(var(--n-option-height) * 4.6)`}}},nodeProps:()=>({style:{justifyContent:`center`}}),show:s===`page`?!1:s===`fast-backward`?this.showFastBackwardMenu:this.showFastForwardMenu,onUpdateShow:e=>{s!==`page`&&(e?s===`fast-backward`?this.showFastBackwardMenu=e:this.showFastForwardMenu=e:(this.showFastBackwardMenu=!1,this.showFastForwardMenu=!1))},options:e.type!==`page`&&e.options?e.options:[],onUpdateValue:this.handleMenuSelect,scrollable:!0,scrollbarProps:this.scrollbarProps,showCheckmark:!1},{default:()=>c})}}),l(`div`,{class:[`${t}-pagination-item`,!I&&`${t}-pagination-item--button`,{[`${t}-pagination-item--disabled`]:i<1||i>=a||n}],onClick:A},I?I({page:i,pageSize:m,pageCount:a,itemCount:this.mergedItemCount,startIndex:this.startIndex,endIndex:this.endIndex}):l(C,{clsPrefix:t},{default:()=>this.rtlEnabled?l(Ke,null):l(Xe,null)})));case`size-picker`:return!v&&s?l(kt,Object.assign({consistentMenuWidth:!1,placeholder:``,showCheckmark:!1,to:this.to},this.selectProps,{size:p,options:g,value:m,disabled:n,scrollbarProps:this.scrollbarProps,theme:u.peers.Select,themeOverrides:u.peerOverrides.Select,onUpdateValue:D})):null;case`quick-jumper`:return!v&&c?l(`div`,{class:`${t}-pagination-quick-jumper`},T?T():ie(this.$slots.goto,()=>[d.goto]),l(De,{value:_,onUpdateValue:E,size:f,placeholder:``,disabled:n,theme:u.peers.Input,themeOverrides:u.peerOverrides.Input,onChange:j})):null;default:return null}}),P?l(`div`,{class:`${t}-pagination-suffix`},P({page:i,pageSize:m,pageCount:a,startIndex:this.startIndex,endIndex:this.endIndex,itemCount:this.mergedItemCount})):null)}});export{zt as t};