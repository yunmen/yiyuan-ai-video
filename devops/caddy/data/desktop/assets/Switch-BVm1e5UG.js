import{$ as e,E as t,O as n,Z as r,v as i}from"./vue-vendor-VvR516j_.js";import{Dt as a,O as o,T as s,_t as c,bt as l,cn as u,dn as d,ft as f,gn as p,h as m,hn as h,in as g,mn as _,mt as v,on as y,p as b,pn as x,pt as S,un as C,y as w}from"./initial-vendor-DGcJKj6B.js";import{t as T}from"./use-merged-state-D72VTG8A.js";var E={buttonHeightSmall:`14px`,buttonHeightMedium:`18px`,buttonHeightLarge:`22px`,buttonWidthSmall:`14px`,buttonWidthMedium:`18px`,buttonWidthLarge:`22px`,buttonWidthPressedSmall:`20px`,buttonWidthPressedMedium:`24px`,buttonWidthPressedLarge:`28px`,railHeightSmall:`18px`,railHeightMedium:`22px`,railHeightLarge:`26px`,railWidthSmall:`32px`,railWidthMedium:`40px`,railWidthLarge:`48px`};function D(e){let{primaryColor:t,opacityDisabled:n,borderRadius:r,textColor3:i}=e;return Object.assign(Object.assign({},E),{iconColor:i,textColor:`white`,loadingColor:t,opacityDisabled:n,railColor:`rgba(0, 0, 0, .14)`,railColorActive:t,buttonBoxShadow:`0 1px 4px 0 rgba(0, 0, 0, 0.3), inset 0 0 1px 0 rgba(0, 0, 0, 0.05)`,buttonColor:`#FFF`,railBorderRadiusSmall:r,railBorderRadiusMedium:r,railBorderRadiusLarge:r,buttonBorderRadiusSmall:r,buttonBorderRadiusMedium:r,buttonBorderRadiusLarge:r,boxShadowFocus:`0 0 0 2px ${g(t,{alpha:.2})}`})}var O={name:`Switch`,common:b,self:D},k=d(`switch`,`
 height: var(--n-height);
 min-width: var(--n-width);
 vertical-align: middle;
 user-select: none;
 -webkit-user-select: none;
 display: inline-flex;
 outline: none;
 justify-content: center;
 align-items: center;
`,[x(`children-placeholder`,`
 height: var(--n-rail-height);
 display: flex;
 flex-direction: column;
 overflow: hidden;
 pointer-events: none;
 visibility: hidden;
 `),x(`rail-placeholder`,`
 display: flex;
 flex-wrap: none;
 `),x(`button-placeholder`,`
 width: calc(1.75 * var(--n-rail-height));
 height: var(--n-rail-height);
 `),d(`base-loading`,`
 position: absolute;
 top: 50%;
 left: 50%;
 transform: translateX(-50%) translateY(-50%);
 font-size: calc(var(--n-button-width) - 4px);
 color: var(--n-loading-color);
 transition: color .3s var(--n-bezier);
 `,[w({left:`50%`,top:`50%`,originalTransform:`translateX(-50%) translateY(-50%)`})]),x(`checked, unchecked`,`
 transition: color .3s var(--n-bezier);
 color: var(--n-text-color);
 box-sizing: border-box;
 position: absolute;
 white-space: nowrap;
 top: 0;
 bottom: 0;
 display: flex;
 align-items: center;
 line-height: 1;
 `),x(`checked`,`
 right: 0;
 padding-right: calc(1.25 * var(--n-rail-height) - var(--n-offset));
 `),x(`unchecked`,`
 left: 0;
 justify-content: flex-end;
 padding-left: calc(1.25 * var(--n-rail-height) - var(--n-offset));
 `),C(`&:focus`,[x(`rail`,`
 box-shadow: var(--n-box-shadow-focus);
 `)]),_(`round`,[x(`rail`,`border-radius: calc(var(--n-rail-height) / 2);`,[x(`button`,`border-radius: calc(var(--n-button-height) / 2);`)])]),h(`disabled`,[h(`icon`,[_(`rubber-band`,[_(`pressed`,[x(`rail`,[x(`button`,`max-width: var(--n-button-width-pressed);`)])]),x(`rail`,[C(`&:active`,[x(`button`,`max-width: var(--n-button-width-pressed);`)])]),_(`active`,[_(`pressed`,[x(`rail`,[x(`button`,`left: calc(100% - var(--n-offset) - var(--n-button-width-pressed));`)])]),x(`rail`,[C(`&:active`,[x(`button`,`left: calc(100% - var(--n-offset) - var(--n-button-width-pressed));`)])])])])])]),_(`active`,[x(`rail`,[x(`button`,`left: calc(100% - var(--n-button-width) - var(--n-offset))`)])]),x(`rail`,`
 overflow: hidden;
 height: var(--n-rail-height);
 min-width: var(--n-rail-width);
 border-radius: var(--n-rail-border-radius);
 cursor: pointer;
 position: relative;
 transition:
 opacity .3s var(--n-bezier),
 background .3s var(--n-bezier),
 box-shadow .3s var(--n-bezier);
 background-color: var(--n-rail-color);
 `,[x(`button-icon`,`
 color: var(--n-icon-color);
 transition: color .3s var(--n-bezier);
 font-size: calc(var(--n-button-height) - 4px);
 position: absolute;
 left: 0;
 right: 0;
 top: 0;
 bottom: 0;
 display: flex;
 justify-content: center;
 align-items: center;
 line-height: 1;
 `,[w()]),x(`button`,`
 align-items: center; 
 top: var(--n-offset);
 left: var(--n-offset);
 height: var(--n-button-height);
 width: var(--n-button-width-pressed);
 max-width: var(--n-button-width);
 border-radius: var(--n-button-border-radius);
 background-color: var(--n-button-color);
 box-shadow: var(--n-button-box-shadow);
 box-sizing: border-box;
 cursor: inherit;
 content: "";
 position: absolute;
 transition:
 background-color .3s var(--n-bezier),
 left .3s var(--n-bezier),
 opacity .3s var(--n-bezier),
 max-width .3s var(--n-bezier),
 box-shadow .3s var(--n-bezier);
 `)]),_(`active`,[x(`rail`,`background-color: var(--n-rail-color-active);`)]),_(`loading`,[x(`rail`,`
 cursor: wait;
 `)]),_(`disabled`,[x(`rail`,`
 cursor: not-allowed;
 opacity: .5;
 `)])]),A=Object.assign(Object.assign({},o.props),{size:String,value:{type:[String,Number,Boolean],default:void 0},loading:Boolean,defaultValue:{type:[String,Number,Boolean],default:!1},disabled:{type:Boolean,default:void 0},round:{type:Boolean,default:!0},"onUpdate:value":[Function,Array],onUpdateValue:[Function,Array],checkedValue:{type:[String,Number,Boolean],default:!0},uncheckedValue:{type:[String,Number,Boolean],default:!1},railStyle:Function,rubberBand:{type:Boolean,default:!0},spinProps:Object,onChange:[Function,Array]}),j,M=t({name:`Switch`,props:A,slots:Object,setup(t){j===void 0&&(j=typeof CSS<`u`?CSS.supports===void 0?!1:CSS.supports(`width`,`max(1px)`):!0);let{mergedClsPrefixRef:n,inlineThemeDisabled:s,mergedComponentPropsRef:c}=v(t),l=o(`Switch`,`-switch`,k,O,t,n),d=f(t,{mergedSize(e){return t.size===void 0?e?e.mergedSize.value:c?.value?.Switch?.size||`medium`:t.size}}),{mergedSizeRef:m,mergedDisabledRef:h}=d,g=r(t.defaultValue),_=T(e(t,`value`),g),b=i(()=>_.value===t.checkedValue),x=r(!1),C=r(!1),w=i(()=>{let{railStyle:e}=t;if(e)return e({focused:C.value,checked:b.value})});function E(e){let{"onUpdate:value":n,onChange:r,onUpdateValue:i}=t,{nTriggerFormInput:o,nTriggerFormChange:s}=d;n&&a(n,e),i&&a(i,e),r&&a(r,e),g.value=e,o(),s()}function D(){let{nTriggerFormFocus:e}=d;e()}function A(){let{nTriggerFormBlur:e}=d;e()}function M(){t.loading||h.value||(_.value===t.checkedValue?E(t.uncheckedValue):E(t.checkedValue))}function N(){C.value=!0,D()}function P(){C.value=!1,A(),x.value=!1}function F(e){t.loading||h.value||e.key===` `&&(_.value===t.checkedValue?E(t.uncheckedValue):E(t.checkedValue),x.value=!1)}function I(e){t.loading||h.value||e.key===` `&&(e.preventDefault(),x.value=!0)}let L=i(()=>{let{value:e}=m,{self:{opacityDisabled:t,railColor:n,railColorActive:r,buttonBoxShadow:i,buttonColor:a,boxShadowFocus:o,loadingColor:s,textColor:c,iconColor:d,[p(`buttonHeight`,e)]:f,[p(`buttonWidth`,e)]:h,[p(`buttonWidthPressed`,e)]:g,[p(`railHeight`,e)]:_,[p(`railWidth`,e)]:v,[p(`railBorderRadius`,e)]:b,[p(`buttonBorderRadius`,e)]:x},common:{cubicBezierEaseInOut:S}}=l.value,C,w,T;return j?(C=`calc((${_} - ${f}) / 2)`,w=`max(${_}, ${f})`,T=`max(${v}, calc(${v} + ${f} - ${_}))`):(C=u((y(_)-y(f))/2),w=u(Math.max(y(_),y(f))),T=y(_)>y(f)?v:u(y(v)+y(f)-y(_))),{"--n-bezier":S,"--n-button-border-radius":x,"--n-button-box-shadow":i,"--n-button-color":a,"--n-button-width":h,"--n-button-width-pressed":g,"--n-button-height":f,"--n-height":w,"--n-offset":C,"--n-opacity-disabled":t,"--n-rail-border-radius":b,"--n-rail-color":n,"--n-rail-color-active":r,"--n-rail-height":_,"--n-rail-width":v,"--n-width":T,"--n-box-shadow-focus":o,"--n-loading-color":s,"--n-text-color":c,"--n-icon-color":d}}),R=s?S(`switch`,i(()=>m.value[0]),L,t):void 0;return{handleClick:M,handleBlur:P,handleFocus:N,handleKeyup:F,handleKeydown:I,mergedRailStyle:w,pressed:x,mergedClsPrefix:n,mergedValue:_,checked:b,mergedDisabled:h,cssVars:s?void 0:L,themeClass:R?.themeClass,onRender:R?.onRender}},render(){let{mergedClsPrefix:e,mergedDisabled:t,checked:r,mergedRailStyle:i,onRender:a,$slots:o}=this;a?.();let{checked:u,unchecked:d,icon:f,"checked-icon":p,"unchecked-icon":h}=o,g=!(c(f)&&c(p)&&c(h));return n(`div`,{role:`switch`,"aria-checked":r,class:[`${e}-switch`,this.themeClass,g&&`${e}-switch--icon`,r&&`${e}-switch--active`,t&&`${e}-switch--disabled`,this.round&&`${e}-switch--round`,this.loading&&`${e}-switch--loading`,this.pressed&&`${e}-switch--pressed`,this.rubberBand&&`${e}-switch--rubber-band`],tabindex:this.mergedDisabled?void 0:0,style:this.cssVars,onClick:this.handleClick,onFocus:this.handleFocus,onBlur:this.handleBlur,onKeyup:this.handleKeyup,onKeydown:this.handleKeydown},n(`div`,{class:`${e}-switch__rail`,"aria-hidden":`true`,style:i},l(u,t=>l(d,r=>t||r?n(`div`,{"aria-hidden":!0,class:`${e}-switch__children-placeholder`},n(`div`,{class:`${e}-switch__rail-placeholder`},n(`div`,{class:`${e}-switch__button-placeholder`}),t),n(`div`,{class:`${e}-switch__rail-placeholder`},n(`div`,{class:`${e}-switch__button-placeholder`}),r)):null)),n(`div`,{class:`${e}-switch__button`},l(f,t=>l(p,r=>l(h,i=>n(s,null,{default:()=>this.loading?n(m,Object.assign({key:`loading`,clsPrefix:e,strokeWidth:20},this.spinProps)):this.checked&&(r||t)?n(`div`,{class:`${e}-switch__button-icon`,key:r?`checked-icon`:`icon`},r||t):!this.checked&&(i||t)?n(`div`,{class:`${e}-switch__button-icon`,key:i?`unchecked-icon`:`icon`},i||t):null})))),l(u,t=>t&&n(`div`,{key:`checked`,class:`${e}-switch__checked`},t)),l(d,t=>t&&n(`div`,{key:`unchecked`,class:`${e}-switch__unchecked`},t)))))}});export{M as t};