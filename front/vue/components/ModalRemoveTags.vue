<template>
    <div class="modal fade" id="tagRemoveModal" tabindex="-1" role="dialog" aria-labelledby="tagRemoveModalLabel" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered modal-md" id="modaltag" role="document">
        <div class="modal-content">
        <form method="post" action="#" id="formrmtag">
            <div class="modal-body">
            
                <input type="hidden" class="form-control" id="docidrmv" name="document" value="0">
                <div class="form-row form-group justify-content-center">
                <label class="col-form-label">Select tag :</label>
                <select v-bind:name="'tags'" v-bind:id="'tag'" v-model="valuesselected" multiple>
                    <option v-for="ctag in docustomstagsrmid" :key="ctag.value" v-bind:value="ctag.value">
                        {{ ctag.label }}
                    </option>
                </select>
                

            </div>
            </div>
            <div><h5 id="errortag">{{ form_field_errors}}</h5></div>
            <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
            <button id="rmvtags" type="button" class="btn btn-primary" v-on:click="removetaglist">Unassign tag</button>
            </div>
            </form>
        </div>
        </div>
    </div>
</template>

<script>
export default {
    data () {
        return {
            valuesselected: [],
            docustomstagsrmid: []
        }
    },
    computed: {
        docidrmv() {
            return this.$store.state.documentslist.documentID;
        },
        form_field_errors() {
            return this.$store.state.documentslist.form_field_errors;
        }
    },
    methods: {
        resetTagsList(tab, bool){
            //this.instanceAutocomplete.reset();
        },
        async removetaglist(){
            await this.$store.dispatch('documentslist/unassigntags', buildjsondata(document.getElementById("formrmtag").elements));
            $("#tagRemoveModal").modal('hide');
        },
        buildjsondata(el){
            let element = {};
            let tabindex = [];
            for(let i = 0; i < el.length; i++){
                if((el[i].value.toLowerCase() != "button") && (el[i].value.toLowerCase() != "submit") && (el[i].value != "")){
                    Object.defineProperty(element, el[i].name, {
                        value: el[i].value
                    });
                    tabindex.push(el[i].name.toString());
                }
            }
            return JSON.stringify(element, tabindex);
        }
    },
    watch: {
        "$store.state.documentslist.customstagsrmv": {
        handler: function(nv) {
            this.docustomstagsrmid = nv
        },
        immediate: true 
        }
    }
}
</script>

<style scoped>
</style>