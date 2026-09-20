<template>
    <el-drawer v-model="visible" direction="rtl" size="800">
    <template #header>
      <h4>权限设置</h4>
    </template>
    <template #default>
        <el-tree ref="menu" node-key="id" :data="menu.list" :props="menu.props" show-checkbox default-expand-all></el-tree>
    </template>
    <template #footer>
      <div style="flex: auto">
        <el-button @click="visible=false">取消</el-button>
        <el-button type="primary" :loading="isSaveing" @click="save">保存</el-button>
      </div>
    </template>
  </el-drawer>
</template>

<script>
export default {
    data(){
        return {
            visible: false,
            roleId: undefined,
            isSaveing: false,
            menu: {
                list: [],
                checked: [],
                props: {
                    label: (data)=>{
                        return data.meta.title
                    }
                }
            },
        }
    },
    mounted(){
        this.getMenu()
    },
    methods:{
        open(){
            this.visible = true;
            return this;
        },
        //传递roleId
        setData(row) {
            this.roleId = row.id;
        },
        //获取角色的菜单权限
        async getRoleMenu() {
        let data = { id: this.roleId }
        var res = await this.$API.system.role.menu.get(data);
        if (res.code == 1) {
            this.menu.checked = res.data;
            this.$nextTick(() => {
                let filterKeys = this.menu.checked.filter(key => this.$refs.menu.getNode(key).isLeaf)
                this.$refs.menu.setCheckedKeys(filterKeys, true)
            })
        }
        },
        //获取自己所拥有的所有菜单
        async getMenu(){
            var res = await this.$API.myself.menus.get()
            if(res.code == 1){
                this.menu.list = res.data.menus;
                this.getRoleMenu();
            }

        },
        //保存角色权限
        async save(){
            this.isSaveing = true;
            //选中的和半选的合并后传值接口
            var checkedKeys = this.$refs.menu.getCheckedKeys().concat(this.$refs.menu.getHalfCheckedKeys())
            let data = { id: this.roleId, menus: checkedKeys}
            var res = await this.$API.system.role.permission.get(data);
            if (res.code == 1) {
                this.isSaveing = false;
                this.visible = false;
                this.$message.success("操作成功")
            }
        }
    }
}
</script>

