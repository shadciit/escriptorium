<template>
    <div class="modal fade" id="tagAssignModal" tabindex="-1" role="dialog" aria-labelledby="exampleModalLabel" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered modal-md" id="modaltag" role="document">
        <div class="modal-content">
        <form method="post" action="/documenttag/manage/" id="createtagform">
            <div class="modal-body">
            
                <div class="form-row form-group justify-content-center">
                <label class="col-form-label">Select tag</label>
                <select v-bind:name="'pk'" v-bind:id="'pk'">
                    <option value="" selected></option>
                    <option v-for="ctag in docustomstagscid" :key="ctag.value" v-bind:value="ctag.value">
                        {{ ctag.label }}
                    </option>
                </select>
                </div>
                <div class="form-row form-group justify-content-center text-form"><h4>Or create a new</h4></div>
                <div class="form-group">
                    <label class="col-form-label">Name :</label>
                    <input type="text" class="form-control" v-bind:id="'id_name'" v-bind:name="'name'">
                </div>
                <div class="form-group">
                    <label class="col-form-label">Priority :</label>
                    <select v-model="selected" v-bind:name="'priority'" v-bind:id="'priority'">
                        <option v-for="option in priorityTags" :key="option.value" v-bind:value="option.value">
                            {{ option.text }}
                        </option>
                    </select>
                <input type="hidden" class="form-control" id="docid" name="document" v-model="docid">
                </div>
            
            </div>
            <div><h5 id="errortag">{{ form_field_errors }}</h5></div>
            <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
            <button type="button" id="assigntag" class="btn btn-primary" v-on:click="assigntag()">Assign tag</button>
            </div>
            </form>
        </div>
        </div>
  </div>
</template>

<script>

export default {
    data(){
        return {
                selected: 1,
                priorityTags: [
                        { text: 'Very high', value: 5 },
                        { text: 'High', value: 4 },
                        { text: 'Medium', value: 3 },
                        { text: 'Low', value: 2 },
                        { text: 'Very low', value: 1 }
                    ]
                }
    },
    computed: {
        docid() {
            return this.$store.state.documentslist.documentID;
        },
        docustomstagscid() {
            return this.$store.state.documentslist.maptags;
        },
        form_field_errors() {
            return this.$store.state.documentslist.form_field_errors;
        }
    },
    /*
    watch: {
        "$store.state.documentslist.customstags": {
        handler: function(nv) {
            this.docustomstagscid = this.$store.state.documentslist.maptags
        },
        immediate: true 
        }
    },*/
    methods: {
        async assigntag(){
            await this.$store.dispatch('documentslist/assigntags', this.buildjsondata());
            $("#tagAssignModal").modal('hide');
        },
        buildjsondata(){
            let element = {};
            let x = document.getElementById("createtagform").elements;
            let tabindex = [];
            for(let i = 0; i < document.getElementById("createtagform").elements.length; i++){
                if((x[i].value.toLowerCase() != "button") && (x[i].value.toLowerCase() != "submit") && (x[i].value != "")){
                    Object.defineProperty(element, x[i].name, {
                        value: x[i].value
                    });
                    tabindex.push(x[i].name.toString());
                }
            }
            if(!tabindex.includes('pk')) {
                Object.defineProperty(element, "pk", {
                value: ""
                });
                tabindex.push("pk");
            }
            return JSON.stringify(element, tabindex);
        }
    }
}
</script>

<style scoped>
</style>