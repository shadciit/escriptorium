<template>
    <div class="col panel">
        <div class="tools">
            <button id="importImg"
                    ref="importImg"
                    title="Import image"
                    class="btn btn-sm ml-3 btn-info fas fa-file-import"></button>
            <button id="exportImg"
                    ref="exportImg"
                    title="Export image"
                    class="btn btn-sm ml-3 btn-info fas fa-file-export"></button>
        </div>
        <div class="content-container" ref="formContainer">
            <div ref="contentform" class="content-container">
                <div class="form-group col-xl">
                    <label for="partName">Name :</label>
                    <input type="text" class="w-100" id="partName" ref="partName" v-model="partName" @focusin="editInput(true)" @focusout="updateMetadata($event)">
                </div>
                <div class="form-group col-xl">
                    <input class="w-100 input-group-text" id="partUri" type="text" v-model="partUri" :readonly="true">
                </div>
                <div class="form-group col-xl">
                    <select class="input-group-prepend w-100" @change="updateTypology($event)" v-model="typo" ref="partTypology">
                        <option v-for="t in typologies" :key="t.pk" :value="t.pk" :selected= "t.pk == typo"> {{t.name}} </option>
                    </select>
                </div>
                <div class="form-group col-xl">
                    <div id="metadata-form" class="js-metadata-form">
                        <div class="input-group input-group-sm mb-2 js-formset-row" v-for="metadata in metadatas" :key="metadata.idx">
                            <div class="input-group-sm input-group-prepend w-100">
                                <input type="text" class="form-control input-group-text" :id="'id_metadata_set_key-' + metadata.idx" title="Key" autocomplete="on" placeholder="Key" @focusin="editInput(true)" @focusout="fucusoutInput($event)" :value="metadata.key">
                                <input type="text" class="form-control" :id="'id_metadata_set_value-' + metadata.idx" title="Value" maxlength="512" placeholder="Value" @focusin="editInput(true)" @focusout="fucusoutInput($event)" :value="metadata.value">
                                <button class="btn btn-outline-secondary js-formset-delete" :id="'id_metadata_del-' + metadata.idx" @click="deleteKV($event)" type="button">✗</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
export default {
    data () {
        return {
            metadatas: [],
            pk: 1,
            pk_md: 1,
            _name: null,
            typo: ""
        }
    },
    computed: {
        partName: {
            get: function () {
                this._name = this.$store.state.parts.name;
                return this._name ? this._name : this.$store.state.parts.filename.split('.')[0];
            },
            set: function (newValue) {
                this._name = this.$store.state.parts.name;
            }
        },
        partUri() {
            return this.$store.state.parts.filename
        },
        typology() {
            return this.$store.state.parts.typology
        },
        typologies() {
            return this.$store.state.parts.typologies
        }
    },
    created(){
        this.$store.dispatch('parts/fetchPartTypologies')
    },
    mounted(){
        this.metadatas.push({pk: "", key: "", value: "", idx: this.pk_md})
        this.typo = (this.typology) ? this.typology: ""
    },
    methods: {
        async updateMetadata(ev){
            this.editInput(false)
            await this.$store.dispatch('parts/updatePartName', {"name": ev.target.value})
        },
        async updateTypology(ev){
            await this.$store.dispatch('parts/updatePartTypology', {"typology": ev.target.value})
        },
        async addKV(ev){
            let tab = ev.target.id.split('-');
            if(tab[1]){
                const index = this.metadatas.findIndex(t => t.idx == tab[1])
                let obj = this.metadatas[index]
                if(tab[0].includes("key")) obj = {pk: obj.pk, key: ev.target.value, value: obj.value, idx: tab[1]}
                else if(tab[0].includes("value")) obj = {pk: obj.pk, key: obj.key, value: ev.target.value, idx: tab[1]}
                
                if(obj.pk){
                    let _obj = obj
                    _obj["key"] = {name: obj.key}
                    await this.$store.dispatch('parts/updatePartMetadata', _obj)
                }
                this.metadatas.splice(index, 1, obj)
            }

            let newObj = this.metadatas.filter(o => (o.pk == "" && o.key != "" && o.value != ""))
            if(newObj.length == 1){
                let singleObj = {pk: newObj[0].pk, key: {name: newObj[0].key}, value: newObj[0].value}
                await this.$store.dispatch('parts/createPartMetadata', singleObj)
            }

            let item = this.metadatas[this.metadatas.length - 1]
            if(item.key != "" || item.value != ""){
                this.metadatas.push({pk: "", key: "", value: "", idx: this.metadatas.length})
            }
        },
        async deleteKV(ev){
            let index = ev.target.id.split('-')[1];
            const idx = this.metadatas.findIndex(t => t.idx == index);
            await this.$store.dispatch('parts/deletePartMetadata', this.metadatas[idx])
            this.metadatas.splice(idx, 1);
        },
        editInput(bool){
            this.$store.commit('document/setBlockShortcuts', bool);
        },
        fucusoutInput(ev){
            this.editInput(false)
            this.addKV(ev)
        },
    },
    watch: {
        "$store.state.parts.metadatas": {
            handler: function(nv) {
                let k = 0
                this.metadatas = nv.map(function(item){
                    return {pk: item.pk, key: item.key.name, value: item.value, idx: k++};
                })
                this.pk_md = this.metadatas.length
            },
            immediate: true,
            deep: true
        }
    }
}
</script>

<style scoped>
</style>