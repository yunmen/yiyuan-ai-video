const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=["assets/scCodeEditor-CCJBhyZM.js","assets/index-BXx5NQlT.js","assets/rolldown-runtime-CMxvf4Kt.js","assets/preload-helper-DWD1lbha.js","assets/element-plus-eH1yeUUx.js","assets/elicons-Ch8_wF58.js","assets/element-plus-CCUMM0y2.css","assets/vue-vendor-BCXqZ8gs.js","assets/modules-nc-fcwuK.js","assets/modules-BZuJ4mmt.css","assets/router-CHpCuAmd.js","assets/index-CTTrgyJW.css","assets/codemirror-B2DeJ9yI.js","assets/codemirror-DVxsWuBW.css","assets/scCodeEditor-CCO-sV8E.css"])))=>i.map(i=>d[i]);
import"./rolldown-runtime-CMxvf4Kt.js";import{Ft as e,Ht as t,It as n,Ut as r,Vt as i,Yt as a,cn as o,fn as s,xn as c}from"./elicons-Ch8_wF58.js";import{Et as l,Z as u,mt as d,nt as f,tt as p,ut as m}from"./element-plus-eH1yeUUx.js";import{t as h}from"./preload-helper-DWD1lbha.js";import{i as g}from"./index-BXx5NQlT.js";a();var _={name:`codeeditor`,components:{scCodeEditor:r(()=>h(()=>import(`./scCodeEditor-CCJBhyZM.js`),__vite__mapDeps([0,1,2,3,4,5,6,7,8,9,10,11,12,13,14])))},data(){return{json:`{
	"name": "SCUI",
	"menu": [
		{
			"title": "VUE 3",
			"type": true,
			"link": "https://v3.cn.vuejs.org"
		},
		{
			"title": "elementplus",
			"type": false,
			"link": "https://element-plus.gitee.io"
		}
	]
}`,js:`// Demo code (the actual new parser character stream implementation)
function StringStream(string) {
	this.pos = 0;
	this.string = string;
}`,sql:"SELECT `author`, `title` FROM `posts`\nWHERE `status` = 'draft' AND `author` IN('author1','author2')\nORDER BY `created_at` DESC, `id` DESC LIMIT 0, 10;"}},methods:{getCode(){this.$message(`请查看控制台`),console.log(this.json)},getValue(){this.$message(`请查看控制台`);var e=this.$refs.editor.coder.getValue();console.log(e)},setValue(){this.$refs.editor.coder.setValue(`{"key":"newValue"}`)}}},v={style:{"margin-top":`15px`}};function y(r,a,h,g,_,y){let b=l,x=s(`sc-code-editor`),S=d,C=m,w=p,T=f,E=u;return o(),n(E,null,{default:c(()=>[t(b,{title:`感谢codeMirror组件`,type:`success`,style:{"margin-bottom":`20px`}}),t(T,{gutter:15},{default:c(()=>[t(w,{lg:24},{default:c(()=>[t(C,{shadow:`never`,header:`JSON`},{default:c(()=>[t(x,{ref:`editor`,modelValue:_.json,"onUpdate:modelValue":a[0]||=e=>_.json=e,mode:`javascript`,height:200},null,8,[`modelValue`]),e(`div`,v,[t(S,{type:`primary`,onClick:y.getCode},{default:c(()=>[...a[3]||=[i(`获取v-model`,-1)]]),_:1},8,[`onClick`]),t(S,{type:`primary`,onClick:y.getValue},{default:c(()=>[...a[4]||=[i(`getValue()`,-1)]]),_:1},8,[`onClick`]),t(S,{type:`primary`,onClick:y.setValue},{default:c(()=>[...a[5]||=[i(`setValue()`,-1)]]),_:1},8,[`onClick`])])]),_:1})]),_:1}),t(w,{lg:12},{default:c(()=>[t(C,{shadow:`never`,header:`javascript Darcula主题`},{default:c(()=>[t(x,{modelValue:_.js,"onUpdate:modelValue":a[1]||=e=>_.js=e,mode:`javascript`,theme:`darcula`},null,8,[`modelValue`])]),_:1})]),_:1}),t(w,{lg:12},{default:c(()=>[t(C,{shadow:`never`,header:`SQL`},{default:c(()=>[t(x,{modelValue:_.sql,"onUpdate:modelValue":a[2]||=e=>_.sql=e,mode:`sql`},null,8,[`modelValue`])]),_:1})]),_:1})]),_:1})]),_:1})}var b=g(_,[[`render`,y]]);export{b as default};