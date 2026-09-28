import{$ as e,A as t,F as n,H as r,K as i,L as a,N as o,O as s,P as c,R as l,Y as u,b as d,f,g as p,j as m,q as h,s as g,tt as _,z as v}from"./vue-vendor-ZQDshSmE.js";import{Bt as y,D as b,Dt as x,E as S,Ft as C,It as w,Mt as T,O as E,Rt as D,Zt as O,bt as k,cn as A,dn as j,en as M,f as N,ft as ee,gn as P,gt as F,h as I,hn as L,in as R,j as te,l as z,ln as ne,mn as B,mt as re,on as V,p as H,pn as U,pt as ie,sn as W,u as G,un as K,vt as q,xt as J}from"./initial-vendor-CXHx5mAA.js";import{c as Y,d as ae,f as oe,g as X,i as Z,l as se,m as Q,p as ce,s as le,t as ue,u as de}from"./Popover-BbumLWk_.js";import{a as fe,i as pe,o as $,r as me,t as he}from"./Tag-CoOa412W.js";import{t as ge}from"./use-merged-state-Doa9wl0w.js";import{t as _e}from"./use-compitable-BTP-85S-.js";import{n as ve}from"./Eye-DHQargfb.js";import{r as ye}from"./Input-B8Pp_Tpu.js";import{n as be,t as xe}from"./Empty-Bb2Vmft2.js";function Se(e){return e&-e}var Ce=class{constructor(e,t){this.l=e,this.min=t;let n=Array(e+1);for(let t=0;t<e+1;++t)n[t]=0;this.ft=n}add(e,t){if(t===0)return;let{l:n,ft:r}=this;for(e+=1;e<=n;)r[e]+=t,e+=Se(e)}get(e){return this.sum(e+1)-this.sum(e)}sum(e){if(e===void 0&&(e=this.l),e<=0)return 0;let{ft:t,min:n,l:r}=this;if(e>r)throw Error("[FinweckTree.sum]: `i` is larger than length.");let i=e*n;for(;e>0;)i+=t[e],e-=Se(e);return i}getBound(e){let t=0,n=this.l;for(;n>t;){let r=Math.floor((t+n)/2),i=this.sum(r);if(i>e){n=r;continue}else if(i<e){if(t===r)return this.sum(t+1)<=e?t+1:r;t=r}else return r}return t}},we;function Te(){return typeof document>`u`?!1:(we===void 0&&(we=`matchMedia`in window?window.matchMedia(`(pointer:coarse)`).matches:!1),we)}var Ee;function De(){return typeof document>`u`?1:(Ee===void 0&&(Ee=`chrome`in window?window.devicePixelRatio:1),Ee)}var Oe=`VVirtualListXScroll`;function ke({columnsRef:t,renderColRef:n,renderItemWithColsRef:i}){let a=e(0),o=e(0),s=d(()=>{let e=t.value;if(e.length===0)return null;let n=new Ce(e.length,0);return e.forEach((e,t)=>{n.add(t,e.width)}),n});return r(Oe,{startIndexRef:M(()=>{let e=s.value;return e===null?0:Math.max(e.getBound(o.value)-1,0)}),endIndexRef:M(()=>{let e=s.value;return e===null?0:Math.min(e.getBound(o.value+a.value)+1,t.value.length-1)}),columnsRef:t,renderColRef:n,renderItemWithColsRef:i,getLeft:e=>{let t=s.value;return t===null?0:t.sum(e)}}),{listWidthRef:a,scrollLeftRef:o}}var Ae=s({name:`VirtualListRow`,props:{index:{type:Number,required:!0},item:{type:Object,required:!0}},setup(){let{startIndexRef:e,endIndexRef:t,columnsRef:n,getLeft:r,renderColRef:i,renderItemWithColsRef:a}=m(Oe);return{startIndex:e,endIndex:t,columns:n,renderCol:i,renderItemWithCols:a,getLeft:r}},render(){let{startIndex:e,endIndex:t,columns:n,renderCol:r,renderItemWithCols:i,getLeft:a,item:o}=this;if(i!=null)return i({itemIndex:this.index,startColIndex:e,endColIndex:t,allColumns:n,item:o,getLeft:a});if(r!=null){let i=[];for(let s=e;s<=t;++s){let e=n[s];i.push(r({column:e,left:a(s),item:o}))}return i}return null}}),je=Y(`.v-vl`,{maxHeight:`inherit`,height:`100%`,overflow:`auto`,minWidth:`1px`},[Y(`&:not(.v-vl--show-scrollbar)`,{scrollbarWidth:`none`},[Y(`&::-webkit-scrollbar, &::-webkit-scrollbar-track-piece, &::-webkit-scrollbar-thumb`,{width:0,height:0,display:`none`})])]),Me=s({name:`VirtualList`,inheritAttrs:!1,props:{showScrollbar:{type:Boolean,default:!0},columns:{type:Array,default:()=>[]},renderCol:Function,renderItemWithCols:Function,items:{type:Array,default:()=>[]},itemSize:{type:Number,required:!0},itemResizable:Boolean,itemsStyle:[String,Object],visibleItemsTag:{type:[String,Object],default:`div`},visibleItemsProps:Object,ignoreItemResize:Boolean,onScroll:Function,onWheel:Function,onResize:Function,defaultScrollKey:[Number,String],defaultScrollIndex:Number,keyField:{type:String,default:`key`},paddingTop:{type:[Number,String],default:0},paddingBottom:{type:[Number,String],default:0}},setup(t){let r=D();je.mount({id:`vueuc/virtual-list`,head:!0,anchorMetaName:se,ssr:r}),v(()=>{let{defaultScrollIndex:e,defaultScrollKey:n}=t;e==null?n!=null&&S({key:n}):S({index:e})});let i=!1,a=!1;n(()=>{if(i=!1,!a){a=!0;return}S({top:y.value,left:c.value})}),l(()=>{i=!0,a||=!0});let o=M(()=>{if(t.renderCol==null&&t.renderItemWithCols==null||t.columns.length===0)return;let e=0;return t.columns.forEach(t=>{e+=t.width}),e}),s=d(()=>{let e=new Map,{keyField:n}=t;return t.items.forEach((t,r)=>{e.set(t[n],r)}),e}),{scrollLeftRef:c,listWidthRef:u}=ke({columnsRef:_(t,`columns`),renderColRef:_(t,`renderCol`),renderItemWithColsRef:_(t,`renderItemWithCols`)}),f=e(null),p=e(void 0),m=new Map,h=d(()=>{let{items:e,itemSize:n,keyField:r}=t,i=new Ce(e.length,n);return e.forEach((e,t)=>{let n=e[r],a=m.get(n);a!==void 0&&i.add(t,a)}),i}),g=e(0),y=e(0),b=M(()=>Math.max(h.value.getBound(y.value-V(t.paddingTop))-1,0)),x=d(()=>{let{value:e}=p;if(e===void 0)return[];let{items:n,itemSize:r}=t,i=b.value,a=Math.min(i+Math.ceil(e/r+1),n.length-1),o=[];for(let e=i;e<=a;++e)o.push(n[e]);return o}),S=(e,t)=>{if(typeof e==`number`){E(e,t,`auto`);return}let{left:n,top:r,index:i,key:a,position:o,behavior:c,debounce:l=!0}=e;if(n!==void 0||r!==void 0)E(n,r,c);else if(i!==void 0)T(i,c,l);else if(a!==void 0){let e=s.value.get(a);e!==void 0&&T(e,c,l)}else o===`bottom`?E(0,2**53-1,c):o===`top`&&E(0,0,c)},C,w=null;function T(e,n,r){let{value:i}=h,a=i.sum(e)+V(t.paddingTop);if(!r)f.value.scrollTo({left:0,top:a,behavior:n});else{C=e,w!==null&&window.clearTimeout(w),w=window.setTimeout(()=>{C=void 0,w=null},16);let{scrollTop:t,offsetHeight:r}=f.value;if(a>t){let o=i.get(e);a+o<=t+r||f.value.scrollTo({left:0,top:a+o-r,behavior:n})}else f.value.scrollTo({left:0,top:a,behavior:n})}}function E(e,t,n){f.value.scrollTo({left:e,top:t,behavior:n})}function O(e,n){if(i||t.ignoreItemResize||I(n.target))return;let{value:r}=h,a=s.value.get(e),o=r.get(a),c=n.borderBoxSize?.[0]?.blockSize??n.contentRect.height;if(c===o)return;c-t.itemSize===0?m.delete(e):m.set(e,c-t.itemSize);let l=c-o;if(l===0)return;r.add(a,l);let u=f.value;if(u!=null){if(C===void 0){let e=r.sum(a);u.scrollTop>e&&u.scrollBy(0,l)}else (a<C||a===C&&c+r.sum(a)>u.scrollTop+u.offsetHeight)&&u.scrollBy(0,l);F()}g.value++}let k=!Te(),j=!1;function N(e){var n;(n=t.onScroll)==null||n.call(t,e),(!k||!j)&&F()}function ee(e){var n;if((n=t.onWheel)==null||n.call(t,e),k){let t=f.value;if(t!=null){if(e.deltaX===0&&(t.scrollTop===0&&e.deltaY<=0||t.scrollTop+t.offsetHeight>=t.scrollHeight&&e.deltaY>=0))return;e.preventDefault(),t.scrollTop+=e.deltaY/De(),t.scrollLeft+=e.deltaX/De(),F(),j=!0,X(()=>{j=!1})}}}function P(e){if(i||I(e.target))return;if(t.renderCol==null&&t.renderItemWithCols==null){if(e.contentRect.height===p.value)return}else if(e.contentRect.height===p.value&&e.contentRect.width===u.value)return;p.value=e.contentRect.height,u.value=e.contentRect.width;let{onResize:n}=t;n!==void 0&&n(e)}function F(){let{value:e}=f;e!=null&&(y.value=e.scrollTop,c.value=e.scrollLeft)}function I(e){let t=e;for(;t!==null;){if(t.style.display===`none`)return!0;t=t.parentElement}return!1}return{listHeight:p,listStyle:{overflow:`auto`},keyToIndex:s,itemsStyle:d(()=>{let{itemResizable:e}=t,n=A(h.value.sum());return g.value,[t.itemsStyle,{boxSizing:`content-box`,width:A(o.value),height:e?``:n,minHeight:e?n:``,paddingTop:A(t.paddingTop),paddingBottom:A(t.paddingBottom)}]}),visibleItemsStyle:d(()=>(g.value,{transform:`translateY(${A(h.value.sum(b.value))})`})),viewportItems:x,listElRef:f,itemsElRef:e(null),scrollTo:S,handleListResize:P,handleListScroll:N,handleListWheel:ee,handleItemResize:O}},render(){let{itemResizable:e,keyField:n,keyToIndex:r,visibleItemsTag:i}=this;return t(C,{onResize:this.handleListResize},{default:()=>{var a;return t(`div`,o(this.$attrs,{class:[`v-vl`,this.showScrollbar&&`v-vl--show-scrollbar`],onScroll:this.handleListScroll,onWheel:this.handleListWheel,ref:`listElRef`}),[this.items.length===0?(a=this.$slots).empty?.call(a):t(`div`,{ref:`itemsElRef`,class:`v-vl-items`,style:this.itemsStyle},[t(i,Object.assign({class:`v-vl-visible-items`,style:this.visibleItemsStyle},this.visibleItemsProps),{default:()=>{let{renderCol:i,renderItemWithCols:a}=this;return this.viewportItems.map(o=>{let s=o[n],c=r.get(s),l=i==null?void 0:t(Ae,{index:c,item:o}),u=a==null?void 0:t(Ae,{index:c,item:o}),d=this.$slots.default({item:o,renderedCols:l,renderedItemWithCols:u,index:c})[0];return e?t(C,{key:s,onResize:e=>this.handleItemResize(s,e)},{default:()=>d}):(d.key=s,d)})}})])])}})}});function Ne(e,t){t&&(v(()=>{let{value:n}=e;n&&w.registerHandler(n,t)}),i(e,(e,t)=>{t&&w.unregisterHandler(t)},{deep:!1}),a(()=>{let{value:t}=e;t&&w.unregisterHandler(t)}))}function Pe(e){switch(typeof e){case`string`:return e||void 0;case`number`:return String(e);default:return}}function Fe(e){let t=e.filter(e=>e!==void 0);if(t.length!==0)return t.length===1?t[0]:t=>{e.forEach(e=>{e&&e(t)})}}var Ie=s({name:`Checkmark`,render(){return t(`svg`,{xmlns:`http://www.w3.org/2000/svg`,viewBox:`0 0 16 16`},t(`g`,{fill:`none`},t(`path`,{d:`M14.046 3.486a.75.75 0 0 1-.032 1.06l-7.93 7.474a.85.85 0 0 1-1.188-.022l-2.68-2.72a.75.75 0 1 1 1.068-1.053l2.234 2.267l7.468-7.038a.75.75 0 0 1 1.06.032z`,fill:`currentColor`})))}}),Le=s({props:{onFocus:Function,onBlur:Function},setup(e){return()=>t(`div`,{style:`width: 0; height: 0`,tabindex:0,onFocus:e.onFocus,onBlur:e.onBlur})}}),Re={height:`calc(var(--n-option-height) * 7.6)`,paddingTiny:`4px 0`,paddingSmall:`4px 0`,paddingMedium:`4px 0`,paddingLarge:`4px 0`,paddingHuge:`4px 0`,optionPaddingTiny:`0 12px`,optionPaddingSmall:`0 12px`,optionPaddingMedium:`0 12px`,optionPaddingLarge:`0 12px`,optionPaddingHuge:`0 12px`,loadingSize:`18px`};function ze(e){let{borderRadius:t,popoverColor:n,textColor3:r,dividerColor:i,textColor2:a,primaryColorPressed:o,textColorDisabled:s,primaryColor:c,opacityDisabled:l,hoverColor:u,fontSizeTiny:d,fontSizeSmall:f,fontSizeMedium:p,fontSizeLarge:m,fontSizeHuge:h,heightTiny:g,heightSmall:_,heightMedium:v,heightLarge:y,heightHuge:b}=e;return Object.assign(Object.assign({},Re),{optionFontSizeTiny:d,optionFontSizeSmall:f,optionFontSizeMedium:p,optionFontSizeLarge:m,optionFontSizeHuge:h,optionHeightTiny:g,optionHeightSmall:_,optionHeightMedium:v,optionHeightLarge:y,optionHeightHuge:b,borderRadius:t,color:n,groupHeaderTextColor:r,actionDividerColor:i,optionTextColor:a,optionTextColorPressed:o,optionTextColorDisabled:s,optionTextColorActive:c,optionOpacityDisabled:l,optionCheckColor:c,optionColorPending:u,optionColorActive:`rgba(0, 0, 0, 0)`,optionColorActivePending:u,actionTextColor:a,loadingColor:c})}var Be=b({name:`InternalSelectMenu`,common:H,peers:{Scrollbar:N,Empty:be},self:ze}),Ve=s({name:`NBaseSelectGroupHeader`,props:{clsPrefix:{type:String,required:!0},tmNode:{type:Object,required:!0}},setup(){let{renderLabelRef:e,renderOptionRef:t,labelFieldRef:n,nodePropsRef:r}=m(Q);return{labelField:n,nodeProps:r,renderLabel:e,renderOption:t}},render(){let{clsPrefix:e,renderLabel:n,renderOption:r,nodeProps:i,tmNode:{rawNode:a}}=this,o=i?.(a),s=n?n(a,!1):J(a[this.labelField],a,!1),c=t(`div`,Object.assign({},o,{class:[`${e}-base-select-group-header`,o?.class]}),s);return a.render?a.render({node:c,option:a}):r?r({node:c,option:a,selected:!1}):c}});function He(e,n){return t(g,{name:`fade-in-scale-up-transition`},{default:()=>e?t(S,{clsPrefix:n,class:`${n}-base-select-option__check`},{default:()=>t(Ie)}):null})}var Ue=s({name:`NBaseSelectOption`,props:{clsPrefix:{type:String,required:!0},tmNode:{type:Object,required:!0}},setup(e){let{valueRef:t,pendingTmNodeRef:n,multipleRef:r,valueSetRef:i,renderLabelRef:a,renderOptionRef:o,labelFieldRef:s,valueFieldRef:c,showCheckmarkRef:l,nodePropsRef:u,handleOptionClick:d,handleOptionMouseEnter:f}=m(Q),p=M(()=>{let{value:t}=n;return t?e.tmNode.key===t.key:!1});function h(t){let{tmNode:n}=e;n.disabled||d(t,n)}function g(t){let{tmNode:n}=e;n.disabled||f(t,n)}function _(t){let{tmNode:n}=e,{value:r}=p;n.disabled||r||f(t,n)}return{multiple:r,isGrouped:M(()=>{let{tmNode:t}=e,{parent:n}=t;return n&&n.rawNode.type===`group`}),showCheckmark:l,nodeProps:u,isPending:p,isSelected:M(()=>{let{value:n}=t,{value:a}=r;if(n===null)return!1;let o=e.tmNode.rawNode[c.value];if(a){let{value:e}=i;return e.has(o)}else return n===o}),labelField:s,renderLabel:a,renderOption:o,handleMouseMove:_,handleMouseEnter:g,handleClick:h}},render(){let{clsPrefix:e,tmNode:{rawNode:n},isSelected:r,isPending:i,isGrouped:a,showCheckmark:o,nodeProps:s,renderOption:c,renderLabel:l,handleClick:u,handleMouseEnter:d,handleMouseMove:f}=this,p=He(r,e),m=l?[l(n,r),o&&p]:[J(n[this.labelField],n,r),o&&p],h=s?.(n),g=t(`div`,Object.assign({},h,{class:[`${e}-base-select-option`,n.class,h?.class,{[`${e}-base-select-option--disabled`]:n.disabled,[`${e}-base-select-option--selected`]:r,[`${e}-base-select-option--grouped`]:a,[`${e}-base-select-option--pending`]:i,[`${e}-base-select-option--show-checkmark`]:o}],style:[h?.style||``,n.style||``],onClick:Fe([u,h?.onClick]),onMouseenter:Fe([d,h?.onMouseenter]),onMousemove:Fe([f,h?.onMousemove])}),t(`div`,{class:`${e}-base-select-option__content`},m));return n.render?n.render({node:g,option:n,selected:r}):c?c({node:g,option:n,selected:r}):g}}),We=j(`base-select-menu`,`
 line-height: 1.5;
 outline: none;
 z-index: 0;
 position: relative;
 border-radius: var(--n-border-radius);
 transition:
 background-color .3s var(--n-bezier),
 box-shadow .3s var(--n-bezier);
 background-color: var(--n-color);
`,[j(`scrollbar`,`
 max-height: var(--n-height);
 `),j(`virtual-list`,`
 max-height: var(--n-height);
 `),j(`base-select-option`,`
 min-height: var(--n-option-height);
 font-size: var(--n-option-font-size);
 display: flex;
 align-items: center;
 `,[U(`content`,`
 z-index: 1;
 white-space: nowrap;
 text-overflow: ellipsis;
 overflow: hidden;
 `)]),j(`base-select-group-header`,`
 min-height: var(--n-option-height);
 font-size: .93em;
 display: flex;
 align-items: center;
 `),j(`base-select-menu-option-wrapper`,`
 position: relative;
 width: 100%;
 `),U(`loading, empty`,`
 display: flex;
 padding: 12px 32px;
 flex: 1;
 justify-content: center;
 `),U(`loading`,`
 color: var(--n-loading-color);
 font-size: var(--n-loading-size);
 `),U(`header`,`
 padding: 8px var(--n-option-padding-left);
 font-size: var(--n-option-font-size);
 transition: 
 color .3s var(--n-bezier),
 border-color .3s var(--n-bezier);
 border-bottom: 1px solid var(--n-action-divider-color);
 color: var(--n-action-text-color);
 `),U(`action`,`
 padding: 8px var(--n-option-padding-left);
 font-size: var(--n-option-font-size);
 transition: 
 color .3s var(--n-bezier),
 border-color .3s var(--n-bezier);
 border-top: 1px solid var(--n-action-divider-color);
 color: var(--n-action-text-color);
 `),j(`base-select-group-header`,`
 position: relative;
 cursor: default;
 padding: var(--n-option-padding);
 color: var(--n-group-header-text-color);
 `),j(`base-select-option`,`
 cursor: pointer;
 position: relative;
 padding: var(--n-option-padding);
 transition:
 color .3s var(--n-bezier),
 opacity .3s var(--n-bezier);
 box-sizing: border-box;
 color: var(--n-option-text-color);
 opacity: 1;
 `,[B(`show-checkmark`,`
 padding-right: calc(var(--n-option-padding-right) + 20px);
 `),K(`&::before`,`
 content: "";
 position: absolute;
 left: 4px;
 right: 4px;
 top: 0;
 bottom: 0;
 border-radius: var(--n-border-radius);
 transition: background-color .3s var(--n-bezier);
 `),K(`&:active`,`
 color: var(--n-option-text-color-pressed);
 `),B(`grouped`,`
 padding-left: calc(var(--n-option-padding-left) * 1.5);
 `),B(`pending`,[K(`&::before`,`
 background-color: var(--n-option-color-pending);
 `)]),B(`selected`,`
 color: var(--n-option-text-color-active);
 `,[K(`&::before`,`
 background-color: var(--n-option-color-active);
 `),B(`pending`,[K(`&::before`,`
 background-color: var(--n-option-color-active-pending);
 `)])]),B(`disabled`,`
 cursor: not-allowed;
 `,[L(`selected`,`
 color: var(--n-option-text-color-disabled);
 `),B(`selected`,`
 opacity: var(--n-option-opacity-disabled);
 `)]),U(`check`,`
 font-size: 16px;
 position: absolute;
 right: calc(var(--n-option-padding-right) - 4px);
 top: calc(50% - 7px);
 color: var(--n-option-check-color);
 transition: color .3s var(--n-bezier);
 `,[z({enterScale:`0.5`})])])]),Ge=s({name:`InternalSelectMenu`,props:Object.assign(Object.assign({},E.props),{clsPrefix:{type:String,required:!0},scrollable:{type:Boolean,default:!0},treeMate:{type:Object,required:!0},multiple:Boolean,size:{type:String,default:`medium`},value:{type:[String,Number,Array],default:null},autoPending:Boolean,virtualScroll:{type:Boolean,default:!0},show:{type:Boolean,default:!0},labelField:{type:String,default:`label`},valueField:{type:String,default:`value`},loading:Boolean,focusable:Boolean,renderLabel:Function,renderOption:Function,nodeProps:Function,showCheckmark:{type:Boolean,default:!0},onMousedown:Function,onScroll:Function,onFocus:Function,onBlur:Function,onKeyup:Function,onKeydown:Function,onTabOut:Function,onMouseenter:Function,onMouseleave:Function,onResize:Function,resetMenuOnOptionsChange:{type:Boolean,default:!0},inlineThemeDisabled:Boolean,scrollbarProps:Object,onToggle:Function}),setup(t){let{mergedClsPrefixRef:n,mergedRtlRef:o,mergedComponentPropsRef:s}=re(t),l=te(`InternalSelectMenu`,o,n),u=E(`InternalSelectMenu`,`-internal-select-menu`,We,Be,t,_(t,`clsPrefix`)),f=e(null),p=e(null),m=e(null),h=d(()=>t.treeMate.getFlattenedNodes()),g=d(()=>pe(h.value)),y=e(null);function b(){let{treeMate:e}=t,n=null,{value:r}=t;r===null?n=e.getFirstAvailableNode():(n=t.multiple?e.getNode((r||[])[(r||[]).length-1]):e.getNode(r),(!n||n.disabled)&&(n=e.getFirstAvailableNode())),B(n||null)}function x(){let{value:e}=y;e&&!t.treeMate.getNode(e.key)&&(y.value=null)}let S;i(()=>t.show,e=>{e?S=i(()=>t.treeMate,()=>{t.resetMenuOnOptionsChange?(t.autoPending?b():x(),c(H)):x()},{immediate:!0}):S?.()},{immediate:!0}),a(()=>{S?.()});let C=d(()=>V(u.value.self[P(`optionHeight`,t.size)])),w=d(()=>W(u.value.self[P(`padding`,t.size)])),T=d(()=>t.multiple&&Array.isArray(t.value)?new Set(t.value):new Set),D=d(()=>{let e=h.value;return e&&e.length===0}),O=d(()=>s?.value?.Select?.renderEmpty);function k(e){let{onToggle:n}=t;n&&n(e)}function A(e){let{onScroll:n}=t;n&&n(e)}function j(e){var t;(t=m.value)==null||t.sync(),A(e)}function M(){var e;(e=m.value)==null||e.sync()}function N(){let{value:e}=y;return e||null}function ee(e,t){t.disabled||B(t,!1)}function F(e,t){t.disabled||k(t)}function I(e){var n;$(e,`action`)||(n=t.onKeyup)==null||n.call(t,e)}function L(e){var n;$(e,`action`)||(n=t.onKeydown)==null||n.call(t,e)}function R(e){var n;(n=t.onMousedown)==null||n.call(t,e),!t.focusable&&e.preventDefault()}function z(){let{value:e}=y;e&&B(e.getNext({loop:!0}),!0)}function ne(){let{value:e}=y;e&&B(e.getPrev({loop:!0}),!0)}function B(e,t=!1){y.value=e,t&&H()}function H(){var e,n;let r=y.value;if(!r)return;let i=g.value(r.key);i!==null&&(t.virtualScroll?(e=p.value)==null||e.scrollTo({index:i}):(n=m.value)==null||n.scrollTo({index:i,elSize:C.value}))}function U(e){var n;f.value?.contains(e.target)&&((n=t.onFocus)==null||n.call(t,e))}function G(e){var n;f.value?.contains(e.relatedTarget)||(n=t.onBlur)==null||n.call(t,e)}r(Q,{handleOptionMouseEnter:ee,handleOptionClick:F,valueSetRef:T,pendingTmNodeRef:y,nodePropsRef:_(t,`nodeProps`),showCheckmarkRef:_(t,`showCheckmark`),multipleRef:_(t,`multiple`),valueRef:_(t,`value`),renderLabelRef:_(t,`renderLabel`),renderOptionRef:_(t,`renderOption`),labelFieldRef:_(t,`labelField`),valueFieldRef:_(t,`valueField`)}),r(ce,f),v(()=>{let{value:e}=m;e&&e.sync()});let K=d(()=>{let{size:e}=t,{common:{cubicBezierEaseInOut:n},self:{height:r,borderRadius:i,color:a,groupHeaderTextColor:o,actionDividerColor:s,optionTextColorPressed:c,optionTextColor:l,optionTextColorDisabled:d,optionTextColorActive:f,optionOpacityDisabled:p,optionCheckColor:m,actionTextColor:h,optionColorPending:g,optionColorActive:_,loadingColor:v,loadingSize:y,optionColorActivePending:b,[P(`optionFontSize`,e)]:x,[P(`optionHeight`,e)]:S,[P(`optionPadding`,e)]:C}}=u.value;return{"--n-height":r,"--n-action-divider-color":s,"--n-action-text-color":h,"--n-bezier":n,"--n-border-radius":i,"--n-color":a,"--n-option-font-size":x,"--n-group-header-text-color":o,"--n-option-check-color":m,"--n-option-color-pending":g,"--n-option-color-active":_,"--n-option-color-active-pending":b,"--n-option-height":S,"--n-option-opacity-disabled":p,"--n-option-text-color":l,"--n-option-text-color-active":f,"--n-option-text-color-disabled":d,"--n-option-text-color-pressed":c,"--n-option-padding":C,"--n-option-padding-left":W(C,`left`),"--n-option-padding-right":W(C,`right`),"--n-loading-color":v,"--n-loading-size":y}}),{inlineThemeDisabled:q}=t,J=q?ie(`internal-select-menu`,d(()=>t.size[0]),K,t):void 0,Y={selfRef:f,next:z,prev:ne,getPendingTmNode:N};return Ne(f,t.onResize),Object.assign({mergedTheme:u,mergedClsPrefix:n,rtlEnabled:l,virtualListRef:p,scrollbarRef:m,itemSize:C,padding:w,flattenedNodes:h,empty:D,mergedRenderEmpty:O,virtualListContainer(){let{value:e}=p;return e?.listElRef},virtualListContent(){let{value:e}=p;return e?.itemsElRef},doScroll:A,handleFocusin:U,handleFocusout:G,handleKeyUp:I,handleKeyDown:L,handleMouseDown:R,handleVirtualListResize:M,handleVirtualListScroll:j,cssVars:q?void 0:K,themeClass:J?.themeClass,onRender:J?.onRender},Y)},render(){let{$slots:e,virtualScroll:n,clsPrefix:r,mergedTheme:i,themeClass:a,onRender:o}=this;return o?.(),t(`div`,{ref:`selfRef`,tabindex:this.focusable?0:-1,class:[`${r}-base-select-menu`,`${r}-base-select-menu--${this.size}-size`,this.rtlEnabled&&`${r}-base-select-menu--rtl`,a,this.multiple&&`${r}-base-select-menu--multiple`],style:this.cssVars,onFocusin:this.handleFocusin,onFocusout:this.handleFocusout,onKeyup:this.handleKeyUp,onKeydown:this.handleKeyDown,onMousedown:this.handleMouseDown,onMouseenter:this.onMouseenter,onMouseleave:this.onMouseleave},k(e.header,e=>e&&t(`div`,{class:`${r}-base-select-menu__header`,"data-header":!0,key:`header`},e)),this.loading?t(`div`,{class:`${r}-base-select-menu__loading`},t(I,{clsPrefix:r,strokeWidth:20})):this.empty?t(`div`,{class:`${r}-base-select-menu__empty`,"data-empty":!0},q(e.empty,()=>[this.mergedRenderEmpty?.call(this)||t(xe,{theme:i.peers.Empty,themeOverrides:i.peerOverrides.Empty,size:this.size})])):t(G,Object.assign({ref:`scrollbarRef`,theme:i.peers.Scrollbar,themeOverrides:i.peerOverrides.Scrollbar,scrollable:this.scrollable,container:n?this.virtualListContainer:void 0,content:n?this.virtualListContent:void 0,onScroll:n?void 0:this.doScroll},this.scrollbarProps),{default:()=>n?t(Me,{ref:`virtualListRef`,class:`${r}-virtual-list`,items:this.flattenedNodes,itemSize:this.itemSize,showScrollbar:!1,paddingTop:this.padding.top,paddingBottom:this.padding.bottom,onResize:this.handleVirtualListResize,onScroll:this.handleVirtualListScroll,itemResizable:!0},{default:({item:e})=>e.isGroup?t(Ve,{key:e.key,clsPrefix:r,tmNode:e}):e.ignored?null:t(Ue,{clsPrefix:r,key:e.key,tmNode:e})}):t(`div`,{class:`${r}-base-select-menu-option-wrapper`,style:{paddingTop:this.padding.top,paddingBottom:this.padding.bottom}},this.flattenedNodes.map(e=>e.isGroup?t(Ve,{key:e.key,clsPrefix:r,tmNode:e}):t(Ue,{clsPrefix:r,key:e.key,tmNode:e})))}),k(e.action,e=>e&&[t(`div`,{class:`${r}-base-select-menu__action`,"data-action":!0,key:`action`},e),t(Le,{onFocus:this.onTabOut,key:`focus-detector`})]))}}),Ke={paddingSingle:`0 26px 0 12px`,paddingMultiple:`3px 26px 0 12px`,clearSize:`16px`,arrowSize:`16px`};function qe(e){let{borderRadius:t,textColor2:n,textColorDisabled:r,inputColor:i,inputColorDisabled:a,primaryColor:o,primaryColorHover:s,warningColor:c,warningColorHover:l,errorColor:u,errorColorHover:d,borderColor:f,iconColor:p,iconColorDisabled:m,clearColor:h,clearColorHover:g,clearColorPressed:_,placeholderColor:v,placeholderColorDisabled:y,fontSizeTiny:b,fontSizeSmall:x,fontSizeMedium:S,fontSizeLarge:C,heightTiny:w,heightSmall:T,heightMedium:E,heightLarge:D,fontWeight:O}=e;return Object.assign(Object.assign({},Ke),{fontSizeTiny:b,fontSizeSmall:x,fontSizeMedium:S,fontSizeLarge:C,heightTiny:w,heightSmall:T,heightMedium:E,heightLarge:D,borderRadius:t,fontWeight:O,textColor:n,textColorDisabled:r,placeholderColor:v,placeholderColorDisabled:y,color:i,colorDisabled:a,colorActive:i,border:`1px solid ${f}`,borderHover:`1px solid ${s}`,borderActive:`1px solid ${o}`,borderFocus:`1px solid ${s}`,boxShadowHover:`none`,boxShadowActive:`0 0 0 2px ${R(o,{alpha:.2})}`,boxShadowFocus:`0 0 0 2px ${R(o,{alpha:.2})}`,caretColor:o,arrowColor:p,arrowColorDisabled:m,loadingColor:o,borderWarning:`1px solid ${c}`,borderHoverWarning:`1px solid ${l}`,borderActiveWarning:`1px solid ${c}`,borderFocusWarning:`1px solid ${l}`,boxShadowHoverWarning:`none`,boxShadowActiveWarning:`0 0 0 2px ${R(c,{alpha:.2})}`,boxShadowFocusWarning:`0 0 0 2px ${R(c,{alpha:.2})}`,colorActiveWarning:i,caretColorWarning:c,borderError:`1px solid ${u}`,borderHoverError:`1px solid ${d}`,borderActiveError:`1px solid ${u}`,borderFocusError:`1px solid ${d}`,boxShadowHoverError:`none`,boxShadowActiveError:`0 0 0 2px ${R(u,{alpha:.2})}`,boxShadowFocusError:`0 0 0 2px ${R(u,{alpha:.2})}`,colorActiveError:i,caretColorError:u,clearColor:h,clearColorHover:g,clearColorPressed:_})}var Je=b({name:`InternalSelection`,common:H,peers:{Popover:Z},self:qe}),Ye=K([j(`base-selection`,`
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
 `,[j(`base-loading`,`
 color: var(--n-loading-color);
 `),j(`base-selection-tags`,`min-height: var(--n-height);`),U(`border, state-border`,`
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
 `),U(`state-border`,`
 z-index: 1;
 border-color: #0000;
 `),j(`base-suffix`,`
 cursor: pointer;
 position: absolute;
 top: 50%;
 transform: translateY(-50%);
 right: 10px;
 `,[U(`arrow`,`
 font-size: var(--n-arrow-size);
 color: var(--n-arrow-color);
 transition: color .3s var(--n-bezier);
 `)]),j(`base-selection-overlay`,`
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
 `,[U(`wrapper`,`
 flex-basis: 0;
 flex-grow: 1;
 overflow: hidden;
 text-overflow: ellipsis;
 `)]),j(`base-selection-placeholder`,`
 color: var(--n-placeholder-color);
 `,[U(`inner`,`
 max-width: 100%;
 overflow: hidden;
 `)]),j(`base-selection-tags`,`
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
 `),j(`base-selection-label`,`
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
 `,[j(`base-selection-input`,`
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
 `,[U(`content`,`
 text-overflow: ellipsis;
 overflow: hidden;
 white-space: nowrap; 
 `)]),U(`render-label`,`
 color: var(--n-text-color);
 `)]),L(`disabled`,[K(`&:hover`,[U(`state-border`,`
 box-shadow: var(--n-box-shadow-hover);
 border: var(--n-border-hover);
 `)]),B(`focus`,[U(`state-border`,`
 box-shadow: var(--n-box-shadow-focus);
 border: var(--n-border-focus);
 `)]),B(`active`,[U(`state-border`,`
 box-shadow: var(--n-box-shadow-active);
 border: var(--n-border-active);
 `),j(`base-selection-label`,`background-color: var(--n-color-active);`),j(`base-selection-tags`,`background-color: var(--n-color-active);`)])]),B(`disabled`,`cursor: not-allowed;`,[U(`arrow`,`
 color: var(--n-arrow-color-disabled);
 `),j(`base-selection-label`,`
 cursor: not-allowed;
 background-color: var(--n-color-disabled);
 `,[j(`base-selection-input`,`
 cursor: not-allowed;
 color: var(--n-text-color-disabled);
 `),U(`render-label`,`
 color: var(--n-text-color-disabled);
 `)]),j(`base-selection-tags`,`
 cursor: not-allowed;
 background-color: var(--n-color-disabled);
 `),j(`base-selection-placeholder`,`
 cursor: not-allowed;
 color: var(--n-placeholder-color-disabled);
 `)]),j(`base-selection-input-tag`,`
 height: calc(var(--n-height) - 6px);
 line-height: calc(var(--n-height) - 6px);
 outline: none;
 display: none;
 position: relative;
 margin-bottom: 3px;
 max-width: 100%;
 vertical-align: bottom;
 `,[U(`input`,`
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
 `),U(`mirror`,`
 position: absolute;
 left: 0;
 top: 0;
 white-space: pre;
 visibility: hidden;
 user-select: none;
 -webkit-user-select: none;
 opacity: 0;
 `)]),[`warning`,`error`].map(e=>B(`${e}-status`,[U(`state-border`,`border: var(--n-border-${e});`),L(`disabled`,[K(`&:hover`,[U(`state-border`,`
 box-shadow: var(--n-box-shadow-hover-${e});
 border: var(--n-border-hover-${e});
 `)]),B(`active`,[U(`state-border`,`
 box-shadow: var(--n-box-shadow-active-${e});
 border: var(--n-border-active-${e});
 `),j(`base-selection-label`,`background-color: var(--n-color-active-${e});`),j(`base-selection-tags`,`background-color: var(--n-color-active-${e});`)]),B(`focus`,[U(`state-border`,`
 box-shadow: var(--n-box-shadow-focus-${e});
 border: var(--n-border-focus-${e});
 `)])])]))]),j(`base-selection-popover`,`
 margin-bottom: -3px;
 display: flex;
 flex-wrap: wrap;
 margin-right: -8px;
 `),j(`base-selection-tag-wrapper`,`
 max-width: 100%;
 display: inline-flex;
 padding: 0 7px 3px 0;
 `,[K(`&:last-child`,`padding-right: 0;`),j(`tag`,`
 font-size: 14px;
 max-width: 100%;
 `,[U(`content`,`
 line-height: 1.25;
 text-overflow: ellipsis;
 overflow: hidden;
 `)])])]),Xe=s({name:`InternalSelection`,props:Object.assign(Object.assign({},E.props),{clsPrefix:{type:String,required:!0},bordered:{type:Boolean,default:void 0},active:Boolean,pattern:{type:String,default:``},placeholder:String,selectedOption:{type:Object,default:null},selectedOptions:{type:Array,default:null},labelField:{type:String,default:`label`},valueField:{type:String,default:`value`},multiple:Boolean,filterable:Boolean,clearable:Boolean,disabled:Boolean,size:{type:String,default:`medium`},loading:Boolean,autofocus:Boolean,showArrow:{type:Boolean,default:!0},inputProps:Object,focused:Boolean,renderTag:Function,onKeydown:Function,onClick:Function,onBlur:Function,onFocus:Function,onDeleteOption:Function,maxTagCount:[String,Number],ellipsisTagPopoverProps:Object,onClear:Function,onPatternInput:Function,onPatternFocus:Function,onPatternBlur:Function,renderLabel:Function,status:String,inlineThemeDisabled:Boolean,ignoreComposition:{type:Boolean,default:!0},onResize:Function}),setup(t){let{mergedClsPrefixRef:n,mergedRtlRef:r}=re(t),a=te(`InternalSelection`,r,n),o=e(null),s=e(null),l=e(null),u=e(null),f=e(null),p=e(null),m=e(null),g=e(null),y=e(null),b=e(null),x=e(!1),S=e(!1),C=e(!1),w=E(`InternalSelection`,`-internal-selection`,Ye,Je,t,_(t,`clsPrefix`)),T=d(()=>t.clearable&&!t.disabled&&(C.value||t.active)),D=d(()=>t.selectedOption?t.renderTag?t.renderTag({option:t.selectedOption,handleClose:()=>{}}):t.renderLabel?t.renderLabel(t.selectedOption,!0):J(t.selectedOption[t.labelField],t.selectedOption,!0):t.placeholder),O=d(()=>{let e=t.selectedOption;if(e)return e[t.labelField]}),k=d(()=>t.multiple?!!(Array.isArray(t.selectedOptions)&&t.selectedOptions.length):t.selectedOption!==null);function A(){var e;let{value:n}=o;if(n){let{value:r}=s;r&&(r.style.width=`${n.offsetWidth}px`,t.maxTagCount!==`responsive`&&((e=y.value)==null||e.sync({showAllItemsBeforeCalculate:!1})))}}function j(){let{value:e}=b;e&&(e.style.display=`none`)}function M(){let{value:e}=b;e&&(e.style.display=`inline-block`)}i(_(t,`active`),e=>{e||j()}),i(_(t,`pattern`),()=>{t.multiple&&c(A)});function N(e){let{onFocus:n}=t;n&&n(e)}function ee(e){let{onBlur:n}=t;n&&n(e)}function F(e){let{onDeleteOption:n}=t;n&&n(e)}function I(e){let{onClear:n}=t;n&&n(e)}function L(e){let{onPatternInput:n}=t;n&&n(e)}function R(e){(!e.relatedTarget||!l.value?.contains(e.relatedTarget))&&N(e)}function z(e){l.value?.contains(e.relatedTarget)||ee(e)}function ne(e){I(e)}function B(){C.value=!0}function V(){C.value=!1}function H(e){!t.active||!t.filterable||e.target!==s.value&&e.preventDefault()}function U(e){F(e)}let G=e(!1);function K(e){if(e.key===`Backspace`&&!G.value&&!t.pattern.length){let{selectedOptions:e}=t;e?.length&&U(e[e.length-1])}}let q=null;function Y(e){let{value:n}=o;n&&(n.textContent=e.target.value,A()),t.ignoreComposition&&G.value?q=e:L(e)}function ae(){G.value=!0}function oe(){G.value=!1,t.ignoreComposition&&L(q),q=null}function X(e){var n;S.value=!0,(n=t.onPatternFocus)==null||n.call(t,e)}function Z(e){var n;S.value=!1,(n=t.onPatternBlur)==null||n.call(t,e)}function se(){var e,n;if(t.filterable)S.value=!1,(e=p.value)==null||e.blur(),(n=s.value)==null||n.blur();else if(t.multiple){let{value:e}=u;e?.blur()}else{let{value:e}=f;e?.blur()}}function Q(){var e,n,r;t.filterable?(S.value=!1,(e=p.value)==null||e.focus()):t.multiple?(n=u.value)==null||n.focus():(r=f.value)==null||r.focus()}function ce(){let{value:e}=s;e&&(M(),e.focus())}function le(){let{value:e}=s;e&&e.blur()}function ue(e){let{value:t}=m;t&&t.setTextContent(`+${e}`)}function de(){let{value:e}=g;return e}function fe(){return s.value}let pe=null;function $(){pe!==null&&window.clearTimeout(pe)}function me(){t.active||($(),pe=window.setTimeout(()=>{k.value&&(x.value=!0)},100))}function he(){$()}function ge(e){e||($(),x.value=!1)}i(k,e=>{e||(x.value=!1)}),v(()=>{h(()=>{let e=p.value;e&&(t.disabled?e.removeAttribute(`tabindex`):e.tabIndex=S.value?-1:0)})}),Ne(l,t.onResize);let{inlineThemeDisabled:_e}=t,ve=d(()=>{let{size:e}=t,{common:{cubicBezierEaseInOut:n},self:{fontWeight:r,borderRadius:i,color:a,placeholderColor:o,textColor:s,paddingSingle:c,paddingMultiple:l,caretColor:u,colorDisabled:d,textColorDisabled:f,placeholderColorDisabled:p,colorActive:m,boxShadowFocus:h,boxShadowActive:g,boxShadowHover:_,border:v,borderFocus:y,borderHover:b,borderActive:x,arrowColor:S,arrowColorDisabled:C,loadingColor:T,colorActiveWarning:E,boxShadowFocusWarning:D,boxShadowActiveWarning:O,boxShadowHoverWarning:k,borderWarning:A,borderFocusWarning:j,borderHoverWarning:M,borderActiveWarning:N,colorActiveError:ee,boxShadowFocusError:F,boxShadowActiveError:I,boxShadowHoverError:L,borderError:R,borderFocusError:te,borderHoverError:z,borderActiveError:ne,clearColor:B,clearColorHover:re,clearColorPressed:V,clearSize:H,arrowSize:U,[P(`height`,e)]:ie,[P(`fontSize`,e)]:G}}=w.value,K=W(c),q=W(l);return{"--n-bezier":n,"--n-border":v,"--n-border-active":x,"--n-border-focus":y,"--n-border-hover":b,"--n-border-radius":i,"--n-box-shadow-active":g,"--n-box-shadow-focus":h,"--n-box-shadow-hover":_,"--n-caret-color":u,"--n-color":a,"--n-color-active":m,"--n-color-disabled":d,"--n-font-size":G,"--n-height":ie,"--n-padding-single-top":K.top,"--n-padding-multiple-top":q.top,"--n-padding-single-right":K.right,"--n-padding-multiple-right":q.right,"--n-padding-single-left":K.left,"--n-padding-multiple-left":q.left,"--n-padding-single-bottom":K.bottom,"--n-padding-multiple-bottom":q.bottom,"--n-placeholder-color":o,"--n-placeholder-color-disabled":p,"--n-text-color":s,"--n-text-color-disabled":f,"--n-arrow-color":S,"--n-arrow-color-disabled":C,"--n-loading-color":T,"--n-color-active-warning":E,"--n-box-shadow-focus-warning":D,"--n-box-shadow-active-warning":O,"--n-box-shadow-hover-warning":k,"--n-border-warning":A,"--n-border-focus-warning":j,"--n-border-hover-warning":M,"--n-border-active-warning":N,"--n-color-active-error":ee,"--n-box-shadow-focus-error":F,"--n-box-shadow-active-error":I,"--n-box-shadow-hover-error":L,"--n-border-error":R,"--n-border-focus-error":te,"--n-border-hover-error":z,"--n-border-active-error":ne,"--n-clear-size":H,"--n-clear-color":B,"--n-clear-color-hover":re,"--n-clear-color-pressed":V,"--n-arrow-size":U,"--n-font-weight":r}}),ye=_e?ie(`internal-selection`,d(()=>t.size[0]),ve,t):void 0;return{mergedTheme:w,mergedClearable:T,mergedClsPrefix:n,rtlEnabled:a,patternInputFocused:S,filterablePlaceholder:D,label:O,selected:k,showTagsPanel:x,isComposing:G,counterRef:m,counterWrapperRef:g,patternInputMirrorRef:o,patternInputRef:s,selfRef:l,multipleElRef:u,singleElRef:f,patternInputWrapperRef:p,overflowRef:y,inputTagElRef:b,handleMouseDown:H,handleFocusin:R,handleClear:ne,handleMouseEnter:B,handleMouseLeave:V,handleDeleteOption:U,handlePatternKeyDown:K,handlePatternInputInput:Y,handlePatternInputBlur:Z,handlePatternInputFocus:X,handleMouseEnterCounter:me,handleMouseLeaveCounter:he,handleFocusout:z,handleCompositionEnd:oe,handleCompositionStart:ae,onPopoverUpdateShow:ge,focus:Q,focusInput:ce,blur:se,blurInput:le,updateCounter:ue,getCounter:de,getTail:fe,renderLabel:t.renderLabel,cssVars:_e?void 0:ve,themeClass:ye?.themeClass,onRender:ye?.onRender}},render(){let{status:e,multiple:n,size:r,disabled:i,filterable:a,maxTagCount:o,bordered:s,clsPrefix:c,ellipsisTagPopoverProps:l,onRender:u,renderTag:d,renderLabel:f}=this;u?.();let m=o===`responsive`,h=typeof o==`number`,g=m||h,_=t(F,null,{default:()=>t(ye,{clsPrefix:c,loading:this.loading,showArrow:this.showArrow,showClear:this.mergedClearable&&this.selected,onClear:this.handleClear},{default:()=>{var e;return(e=this.$slots).arrow?.call(e)}})}),v;if(n){let{labelField:e}=this,n=n=>t(`div`,{class:`${c}-base-selection-tag-wrapper`,key:n.value},d?d({option:n,handleClose:()=>{this.handleDeleteOption(n)}}):t(he,{size:r,closable:!n.disabled,disabled:i,onClose:()=>{this.handleDeleteOption(n)},internalCloseIsButtonTag:!1,internalCloseFocusable:!1},{default:()=>f?f(n,!0):J(n[e],n,!0)})),s=()=>(h?this.selectedOptions.slice(0,o):this.selectedOptions).map(n),u=a?t(`div`,{class:`${c}-base-selection-input-tag`,ref:`inputTagElRef`,key:`__input-tag__`},t(`input`,Object.assign({},this.inputProps,{ref:`patternInputRef`,tabindex:-1,disabled:i,value:this.pattern,autofocus:this.autofocus,class:`${c}-base-selection-input-tag__input`,onBlur:this.handlePatternInputBlur,onFocus:this.handlePatternInputFocus,onKeydown:this.handlePatternKeyDown,onInput:this.handlePatternInputInput,onCompositionstart:this.handleCompositionStart,onCompositionend:this.handleCompositionEnd})),t(`span`,{ref:`patternInputMirrorRef`,class:`${c}-base-selection-input-tag__mirror`},this.pattern)):null,y=m?()=>t(`div`,{class:`${c}-base-selection-tag-wrapper`,ref:`counterWrapperRef`},t(he,{size:r,ref:`counterRef`,onMouseenter:this.handleMouseEnterCounter,onMouseleave:this.handleMouseLeaveCounter,disabled:i})):void 0,b;if(h){let e=this.selectedOptions.length-o;e>0&&(b=t(`div`,{class:`${c}-base-selection-tag-wrapper`,key:`__counter__`},t(he,{size:r,ref:`counterRef`,onMouseenter:this.handleMouseEnterCounter,disabled:i},{default:()=>`+${e}`})))}let x=m?a?t(fe,{ref:`overflowRef`,updateCounter:this.updateCounter,getCounter:this.getCounter,getTail:this.getTail,style:{width:`100%`,display:`flex`,overflow:`hidden`}},{default:s,counter:y,tail:()=>u}):t(fe,{ref:`overflowRef`,updateCounter:this.updateCounter,getCounter:this.getCounter,style:{width:`100%`,display:`flex`,overflow:`hidden`}},{default:s,counter:y}):h&&b?s().concat(b):s(),S=g?()=>t(`div`,{class:`${c}-base-selection-popover`},m?s():this.selectedOptions.map(n)):void 0,C=g?Object.assign({show:this.showTagsPanel,trigger:`hover`,overlap:!0,placement:`top`,width:`trigger`,onUpdateShow:this.onPopoverUpdateShow,theme:this.mergedTheme.peers.Popover,themeOverrides:this.mergedTheme.peerOverrides.Popover},l):null,w=!this.selected&&(!this.active||!this.pattern&&!this.isComposing)?t(`div`,{class:`${c}-base-selection-placeholder ${c}-base-selection-overlay`},t(`div`,{class:`${c}-base-selection-placeholder__inner`},this.placeholder)):null,T=a?t(`div`,{ref:`patternInputWrapperRef`,class:`${c}-base-selection-tags`},x,m?null:u,_):t(`div`,{ref:`multipleElRef`,class:`${c}-base-selection-tags`,tabindex:i?void 0:0},x,_);v=t(p,null,g?t(ue,Object.assign({},C,{scrollable:!0,style:`max-height: calc(var(--v-target-height) * 6.6);`}),{trigger:()=>T,default:S}):T,w)}else if(a){let e=this.pattern||this.isComposing,n=this.active?!e:!this.selected,r=this.active?!1:this.selected;v=t(`div`,{ref:`patternInputWrapperRef`,class:`${c}-base-selection-label`,title:this.patternInputFocused?void 0:Pe(this.label)},t(`input`,Object.assign({},this.inputProps,{ref:`patternInputRef`,class:`${c}-base-selection-input`,value:this.active?this.pattern:``,placeholder:``,readonly:i,disabled:i,tabindex:-1,autofocus:this.autofocus,onFocus:this.handlePatternInputFocus,onBlur:this.handlePatternInputBlur,onInput:this.handlePatternInputInput,onCompositionstart:this.handleCompositionStart,onCompositionend:this.handleCompositionEnd})),r?t(`div`,{class:`${c}-base-selection-label__render-label ${c}-base-selection-overlay`,key:`input`},t(`div`,{class:`${c}-base-selection-overlay__wrapper`},d?d({option:this.selectedOption,handleClose:()=>{}}):f?f(this.selectedOption,!0):J(this.label,this.selectedOption,!0))):null,n?t(`div`,{class:`${c}-base-selection-placeholder ${c}-base-selection-overlay`,key:`placeholder`},t(`div`,{class:`${c}-base-selection-overlay__wrapper`},this.filterablePlaceholder)):null,_)}else v=t(`div`,{ref:`singleElRef`,class:`${c}-base-selection-label`,tabindex:this.disabled?void 0:0},this.label===void 0?t(`div`,{class:`${c}-base-selection-placeholder ${c}-base-selection-overlay`,key:`placeholder`},t(`div`,{class:`${c}-base-selection-placeholder__inner`},this.placeholder)):t(`div`,{class:`${c}-base-selection-input`,title:Pe(this.label),key:`input`},t(`div`,{class:`${c}-base-selection-input__content`},d?d({option:this.selectedOption,handleClose:()=>{}}):f?f(this.selectedOption,!0):J(this.label,this.selectedOption,!0))),_);return t(`div`,{ref:`selfRef`,class:[`${c}-base-selection`,this.rtlEnabled&&`${c}-base-selection--rtl`,this.themeClass,e&&`${c}-base-selection--${e}-status`,{[`${c}-base-selection--active`]:this.active,[`${c}-base-selection--selected`]:this.selected||this.active&&this.pattern,[`${c}-base-selection--disabled`]:this.disabled,[`${c}-base-selection--multiple`]:this.multiple,[`${c}-base-selection--focus`]:this.focused}],style:this.cssVars,onClick:this.onClick,onMouseenter:this.handleMouseEnter,onMouseleave:this.handleMouseLeave,onKeydown:this.onKeydown,onFocusin:this.handleFocusin,onFocusout:this.handleFocusout,onMousedown:this.handleMouseDown},v,s?t(`div`,{class:`${c}-base-selection__border`}):null,s?t(`div`,{class:`${c}-base-selection__state-border`}):null)}});function Ze(e){return e.type===`group`}function Qe(e){return e.type===`ignored`}function $e(e,t){try{return!!(1+t.toString().toLowerCase().indexOf(e.trim().toLowerCase()))}catch{return!1}}function et(e,t){return{getIsGroup:Ze,getIgnored:Qe,getKey(t){return Ze(t)?t.name||t.key||`key-required`:t[e]},getChildren(e){return e[t]}}}function tt(e,t,n,r){if(!t)return e;function i(e){if(!Array.isArray(e))return[];let a=[];for(let o of e)if(Ze(o)){let e=i(o[r]);e.length&&a.push(Object.assign({},o,{[r]:e}))}else if(Qe(o))continue;else t(n,o)&&a.push(o);return a}return i(e)}function nt(e,t,n){let r=new Map;return e.forEach(e=>{Ze(e)?e[n].forEach(e=>{r.set(e[t],e)}):r.set(e[t],e)}),r}function rt(e){let{boxShadow2:t}=e;return{menuBoxShadow:t}}var it=b({name:`Select`,common:H,peers:{InternalSelection:Je,InternalSelectMenu:Be},self:rt}),at=K([j(`select`,`
 z-index: auto;
 outline: none;
 width: 100%;
 position: relative;
 font-weight: var(--n-font-weight);
 `),j(`select-menu`,`
 margin: 4px 0;
 box-shadow: var(--n-menu-box-shadow);
 `,[z({originalTransition:`background-color .3s var(--n-bezier), box-shadow .3s var(--n-bezier)`})])]),ot=s({name:`Select`,props:Object.assign(Object.assign({},E.props),{to:oe.propTo,bordered:{type:Boolean,default:void 0},clearable:Boolean,clearCreatedOptionsOnClear:{type:Boolean,default:!0},clearFilterAfterSelect:{type:Boolean,default:!0},options:{type:Array,default:()=>[]},defaultValue:{type:[String,Number,Array],default:null},keyboard:{type:Boolean,default:!0},value:[String,Number,Array],placeholder:String,menuProps:Object,multiple:Boolean,size:String,menuSize:{type:String},filterable:Boolean,disabled:{type:Boolean,default:void 0},remote:Boolean,loading:Boolean,filter:Function,placement:{type:String,default:`bottom-start`},widthMode:{type:String,default:`trigger`},tag:Boolean,onCreate:Function,fallbackOption:{type:[Function,Boolean],default:void 0},show:{type:Boolean,default:void 0},showArrow:{type:Boolean,default:!0},maxTagCount:[Number,String],ellipsisTagPopoverProps:Object,consistentMenuWidth:{type:Boolean,default:!0},virtualScroll:{type:Boolean,default:!0},labelField:{type:String,default:`label`},valueField:{type:String,default:`value`},childrenField:{type:String,default:`children`},renderLabel:Function,renderOption:Function,renderTag:Function,"onUpdate:value":[Function,Array],inputProps:Object,nodeProps:Function,ignoreComposition:{type:Boolean,default:!0},showOnFocus:Boolean,onUpdateValue:[Function,Array],onBlur:[Function,Array],onClear:[Function,Array],onFocus:[Function,Array],onScroll:[Function,Array],onSearch:[Function,Array],onUpdateShow:[Function,Array],"onUpdate:show":[Function,Array],displayDirective:{type:String,default:`show`},resetMenuOnOptionsChange:{type:Boolean,default:!0},status:String,showCheckmark:{type:Boolean,default:!0},scrollbarProps:Object,onChange:[Function,Array],items:Array}),slots:Object,setup(t){let{mergedClsPrefixRef:n,mergedBorderedRef:r,namespaceRef:a,inlineThemeDisabled:o,mergedComponentPropsRef:s}=re(t),c=E(`Select`,`-select`,at,it,t,n),l=e(t.defaultValue),u=ge(_(t,`value`),l),f=e(!1),p=e(``),m=_e(t,[`items`,`options`]),h=e([]),g=e([]),v=d(()=>g.value.concat(h.value).concat(m.value)),y=d(()=>{let{filter:e}=t;if(e)return e;let{labelField:n,valueField:r}=t;return(e,t)=>{if(!t)return!1;let i=t[n];if(typeof i==`string`)return $e(e,i);let a=t[r];return typeof a==`string`?$e(e,a):typeof a==`number`?$e(e,String(a)):!1}}),b=d(()=>{if(t.remote)return m.value;{let{value:e}=v,{value:n}=p;return!n.length||!t.filterable?e:tt(e,y.value,n,t.childrenField)}}),S=d(()=>{let{valueField:e,childrenField:n}=t,r=et(e,n);return me(b.value,r)}),C=d(()=>nt(v.value,t.valueField,t.childrenField)),w=e(!1),D=ge(_(t,`show`),w),k=e(null),A=e(null),j=e(null),{localeRef:M}=ve(`Select`),N=d(()=>t.placeholder??M.value.placeholder),P=[],F=e(new Map),I=d(()=>{let{fallbackOption:e}=t;if(e===void 0){let{labelField:e,valueField:n}=t;return t=>({[e]:String(t),[n]:t})}return e===!1?!1:t=>Object.assign(e(t),{value:t})});function L(e){let n=t.remote,{value:r}=F,{value:i}=C,{value:a}=I,o=[];return e.forEach(e=>{if(i.has(e))o.push(i.get(e));else if(n&&r.has(e))o.push(r.get(e));else if(a){let t=a(e);t&&o.push(t)}}),o}let R=d(()=>{if(t.multiple){let{value:e}=u;return Array.isArray(e)?L(e):[]}return null}),te=d(()=>{let{value:e}=u;return!t.multiple&&!Array.isArray(e)?e===null?null:L([e])[0]||null:null}),z=ee(t,{mergedSize:e=>{let{size:n}=t;if(n)return n;let{mergedSize:r}=e||{};return r?.value?r.value:s?.value?.Select?.size||`medium`}}),{mergedSizeRef:B,mergedDisabledRef:V,mergedStatusRef:H}=z;function U(e,n){let{onChange:r,"onUpdate:value":i,onUpdateValue:a}=t,{nTriggerFormChange:o,nTriggerFormInput:s}=z;r&&x(r,e,n),a&&x(a,e,n),i&&x(i,e,n),l.value=e,o(),s()}function W(e){let{onBlur:n}=t,{nTriggerFormBlur:r}=z;n&&x(n,e),r()}function G(){let{onClear:e}=t;e&&x(e)}function K(e){let{onFocus:n,showOnFocus:r}=t,{nTriggerFormFocus:i}=z;n&&x(n,e),i(),r&&X()}function q(e){let{onSearch:n}=t;n&&x(n,e)}function J(e){let{onScroll:n}=t;n&&x(n,e)}function Y(){var e;let{remote:n,multiple:r}=t;if(n){let{value:n}=F;if(r){let{valueField:r}=t;(e=R.value)==null||e.forEach(e=>{n.set(e[r],e)})}else{let e=te.value;e&&n.set(e[t.valueField],e)}}}function ae(e){let{onUpdateShow:n,"onUpdate:show":r}=t;n&&x(n,e),r&&x(r,e),w.value=e}function X(){V.value||(ae(!0),w.value=!0,t.filterable&&je())}function Z(){ae(!1)}function se(){p.value=``,g.value=P}let Q=e(!1);function ce(){t.filterable&&(Q.value=!0)}function le(){t.filterable&&(Q.value=!1,D.value||se())}function ue(){V.value||(D.value?t.filterable?je():Z():X())}function de(e){(j.value?.selfRef)?.contains(e.relatedTarget)||(f.value=!1,W(e),Z())}function fe(e){K(e),f.value=!0}function pe(){f.value=!0}function he(e){k.value?.$el.contains(e.relatedTarget)||(f.value=!1,W(e),Z())}function ye(){var e;(e=k.value)==null||e.focus(),Z()}function be(e){D.value&&(k.value?.$el.contains(ne(e))||Z())}function xe(e){if(!Array.isArray(e))return[];if(I.value)return Array.from(e);{let{remote:n}=t,{value:r}=C;if(n){let{value:t}=F;return e.filter(e=>r.has(e)||t.has(e))}else return e.filter(e=>r.has(e))}}function Se(e){Ce(e.rawNode)}function Ce(e){if(V.value)return;let{tag:n,remote:r,clearFilterAfterSelect:i,valueField:a}=t;if(n&&!r){let{value:e}=g,t=e[0]||null;if(t){let e=h.value;e.length?e.push(t):h.value=[t],g.value=P}}if(r&&F.value.set(e[a],e),t.multiple){let t=xe(u.value),o=t.findIndex(t=>t===e[a]);if(~o){if(t.splice(o,1),n&&!r){let t=we(e[a]);~t&&(h.value.splice(t,1),i&&(p.value=``))}}else t.push(e[a]),i&&(p.value=``);U(t,L(t))}else{if(n&&!r){let t=we(e[a]);~t?h.value=[h.value[t]]:h.value=P}Ae(),Z(),U(e[a],e)}}function we(e){return h.value.findIndex(n=>n[t.valueField]===e)}function Te(e){D.value||X();let{value:n}=e.target;p.value=n;let{tag:r,remote:i}=t;if(q(n),r&&!i){if(!n){g.value=P;return}let{onCreate:e}=t,r=e?e(n):{[t.labelField]:n,[t.valueField]:n},{valueField:i,labelField:a}=t;m.value.some(e=>e[i]===r[i]||e[a]===r[a])||h.value.some(e=>e[i]===r[i]||e[a]===r[a])?g.value=P:g.value=[r]}}function Ee(e){e.stopPropagation();let{multiple:n,tag:r,remote:i,clearCreatedOptionsOnClear:a}=t;!n&&t.filterable&&Z(),r&&!i&&a&&(h.value=P),G(),n?U([],[]):U(null,null)}function De(e){!$(e,`action`)&&!$(e,`empty`)&&!$(e,`header`)&&e.preventDefault()}function Oe(e){J(e)}function ke(e){var n,r,i;if(!t.keyboard){e.preventDefault();return}switch(e.key){case` `:if(t.filterable)break;e.preventDefault();case`Enter`:if(!k.value?.isComposing){if(D.value){let e=j.value?.getPendingTmNode();e?Se(e):t.filterable||(Z(),Ae())}else if(X(),t.tag&&Q.value){let e=g.value[0];if(e){let n=e[t.valueField],{value:r}=u;t.multiple&&Array.isArray(r)&&r.includes(n)||Ce(e)}}}e.preventDefault();break;case`ArrowUp`:if(e.preventDefault(),t.loading)return;D.value&&((n=j.value)==null||n.prev());break;case`ArrowDown`:if(e.preventDefault(),t.loading)return;D.value?(r=j.value)==null||r.next():X();break;case`Escape`:D.value&&(T(e),Z()),(i=k.value)==null||i.focus();break}}function Ae(){var e;(e=k.value)==null||e.focus()}function je(){var e;(e=k.value)==null||e.focusInput()}function Me(){var e;D.value&&((e=A.value)==null||e.syncPosition())}Y(),i(_(t,`options`),Y);let Ne={focus:()=>{var e;(e=k.value)==null||e.focus()},focusInput:()=>{var e;(e=k.value)==null||e.focusInput()},blur:()=>{var e;(e=k.value)==null||e.blur()},blurInput:()=>{var e;(e=k.value)==null||e.blurInput()}},Pe=d(()=>{let{self:{menuBoxShadow:e}}=c.value;return{"--n-menu-box-shadow":e}}),Fe=o?ie(`select`,void 0,Pe,t):void 0;return Object.assign(Object.assign({},Ne),{mergedStatus:H,mergedClsPrefix:n,mergedBordered:r,namespace:a,treeMate:S,isMounted:O(),triggerRef:k,menuRef:j,pattern:p,uncontrolledShow:w,mergedShow:D,adjustedTo:oe(t),uncontrolledValue:l,mergedValue:u,followerRef:A,localizedPlaceholder:N,selectedOption:te,selectedOptions:R,mergedSize:B,mergedDisabled:V,focused:f,activeWithoutMenuOpen:Q,inlineThemeDisabled:o,onTriggerInputFocus:ce,onTriggerInputBlur:le,handleTriggerOrMenuResize:Me,handleMenuFocus:pe,handleMenuBlur:he,handleMenuTabOut:ye,handleTriggerClick:ue,handleToggle:Se,handleDeleteOption:Ce,handlePatternInput:Te,handleClear:Ee,handleTriggerBlur:de,handleTriggerFocus:fe,handleKeydown:ke,handleMenuAfterLeave:se,handleMenuClickOutside:be,handleMenuScroll:Oe,handleMenuKeydown:ke,handleMenuMousedown:De,mergedTheme:c,cssVars:o?void 0:Pe,themeClass:Fe?.themeClass,onRender:Fe?.onRender})},render(){return t(`div`,{class:`${this.mergedClsPrefix}-select`},t(ae,null,{default:()=>[t(de,null,{default:()=>t(Xe,{ref:`triggerRef`,inlineThemeDisabled:this.inlineThemeDisabled,status:this.mergedStatus,inputProps:this.inputProps,clsPrefix:this.mergedClsPrefix,showArrow:this.showArrow,maxTagCount:this.maxTagCount,ellipsisTagPopoverProps:this.ellipsisTagPopoverProps,bordered:this.mergedBordered,active:this.activeWithoutMenuOpen||this.mergedShow,pattern:this.pattern,placeholder:this.localizedPlaceholder,selectedOption:this.selectedOption,selectedOptions:this.selectedOptions,multiple:this.multiple,renderTag:this.renderTag,renderLabel:this.renderLabel,filterable:this.filterable,clearable:this.clearable,disabled:this.mergedDisabled,size:this.mergedSize,theme:this.mergedTheme.peers.InternalSelection,labelField:this.labelField,valueField:this.valueField,themeOverrides:this.mergedTheme.peerOverrides.InternalSelection,loading:this.loading,focused:this.focused,onClick:this.handleTriggerClick,onDeleteOption:this.handleDeleteOption,onPatternInput:this.handlePatternInput,onClear:this.handleClear,onBlur:this.handleTriggerBlur,onFocus:this.handleTriggerFocus,onKeydown:this.handleKeydown,onPatternBlur:this.onTriggerInputBlur,onPatternFocus:this.onTriggerInputFocus,onResize:this.handleTriggerOrMenuResize,ignoreComposition:this.ignoreComposition},{arrow:()=>{var e;return[(e=this.$slots).arrow?.call(e)]}})}),t(le,{ref:`followerRef`,show:this.mergedShow,to:this.adjustedTo,teleportDisabled:this.adjustedTo===oe.tdkey,containerClass:this.namespace,width:this.consistentMenuWidth?`target`:void 0,minWidth:`target`,placement:this.placement},{default:()=>t(g,{name:`fade-in-scale-up-transition`,appear:this.isMounted,onAfterLeave:this.handleMenuAfterLeave},{default:()=>{var e;return this.mergedShow||this.displayDirective===`show`?((e=this.onRender)==null||e.call(this),u(t(Ge,Object.assign({},this.menuProps,{ref:`menuRef`,onResize:this.handleTriggerOrMenuResize,inlineThemeDisabled:this.inlineThemeDisabled,virtualScroll:this.consistentMenuWidth&&this.virtualScroll,class:[`${this.mergedClsPrefix}-select-menu`,this.themeClass,this.menuProps?.class],clsPrefix:this.mergedClsPrefix,focusable:!0,labelField:this.labelField,valueField:this.valueField,autoPending:!0,nodeProps:this.nodeProps,theme:this.mergedTheme.peers.InternalSelectMenu,themeOverrides:this.mergedTheme.peerOverrides.InternalSelectMenu,treeMate:this.treeMate,multiple:this.multiple,size:this.menuSize,renderOption:this.renderOption,renderLabel:this.renderLabel,value:this.mergedValue,style:[this.menuProps?.style,this.cssVars],onToggle:this.handleToggle,onScroll:this.handleMenuScroll,onFocus:this.handleMenuFocus,onBlur:this.handleMenuBlur,onKeydown:this.handleMenuKeydown,onTabOut:this.handleMenuTabOut,onMousedown:this.handleMenuMousedown,show:this.mergedShow,showCheckmark:this.showCheckmark,resetMenuOnOptionsChange:this.resetMenuOnOptionsChange,scrollbarProps:this.scrollbarProps}),{empty:()=>{var e;return[(e=this.$slots).empty?.call(e)]},header:()=>{var e;return[(e=this.$slots).header?.call(e)]},action:()=>{var e;return[(e=this.$slots).action?.call(e)]}}),this.displayDirective===`show`?[[f,this.mergedShow],[y,this.handleMenuClickOutside,void 0,{capture:!0}]]:[[y,this.handleMenuClickOutside,void 0,{capture:!0}]])):null}})})]}))}});export{Be as a,Ge as i,it as n,Fe as o,et as r,ot as t};