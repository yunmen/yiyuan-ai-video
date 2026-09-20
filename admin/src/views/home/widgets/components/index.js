import { markRaw } from 'vue'

const resultComps = {}
const requireComponent = import.meta.glob('./*.vue', { eager: true })

Object.keys(requireComponent).forEach(fileName => {
	const comp = requireComponent[fileName]
	resultComps[fileName.replace(/^\.\/(.*)\.\w+$/, '$1')] = comp.default
})

export default markRaw(resultComps)
