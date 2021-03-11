<template>
<div>
    <div class="row">
        <div v-bind:class="'col-12 col-sm-4 col-md-3 col-lg-2'">
            <div v-bind:class="'accordion'">
                <div v-bind:class="'title'">
                    <h3>"Tags"</h3>
                </div>
                <div v-bind:class="'item item-accordion'" v-bind:id="'item1'">
                    <h2>Document tags</h2>
                    <i v-bind:class="'fas fa-chevron-down'" v-bind:id="'j'" v-on:click="animatefunction('j')"></i>
                    <div v-bind:class="'info'" v-bind:id="'info-j'">
                    <ul v-bind:class="'clearfix ckeckbox-list'">
                        <li v-for="tagd in doctagscid" :key="tagd.value">
                            <div v-bind:class="'checkbox'">
                            <input v-if="parseliststr(tagd.value)" type="checkbox" v-bind:class="'filterdoc'" v-bind:id="tagd.value" v-on:click="getFilterDocument" v-bind:name="'categorytag-D'" checked>
                            <input v-else type="checkbox" v-bind:class="'filterdoc'" v-bind:id="tagd.value" v-on:click="getFilterDocument" v-bind:name="'categorytag-D'">
                            <label><span v-bind:class="'badge badge-pill badge-' + definepriority(tagd.priority)">{{tagd.label}}</span></label>
                            </div>
                        </li>
                    </ul>
                    </div>
                </div>
                <div v-bind:class="'item item-accordion'" v-bind:id="'item2'">
                    <h2>Document-part tags</h2>
                    <i v-bind:class="'fas fa-chevron-down'" v-bind:id="'p'" v-on:click="animatefunction('p')"></i>
                    <div v-bind:class="'info'" v-bind:id="'info-p'">
                        <ul v-bind:class="'clearfix ckeckbox-list'">
                            <li v-for="tagi in parttagscid" :key="tagi.value">
                            <div v-bind:class="'checkbox'">
                                <input type="checkbox" v-bind:class="'filterdoc'" v-bind:id="tagi.value" v-bind:name="'categorytag-P'">
                                <label><span v-bind:class="'badge badge-pill badge-' + definepriority(tagi.priority)">{{tagi.label}}</span></label>
                            </div>
                            </li>
                    </ul>
                    </div>
                </div>

                <div v-bind:class="'item item-accordion'">
                    <div style="margin-bottom: -10px;" v-bind:id="'item3S'">
                    <div v-bind:class="'row'" style="margin-left: auto; margin-right: auto;">
                        <div v-bind:class="'col-6'"><h6 v-bind:id="'selectall'" v-on:click="toggleselect('true')">Select all </h6></div>
                        <div v-bind:class="'col-6'"><h6 v-bind:id="'deselectall'" v-on:click="toggleselect('false')">Deselect all </h6></div>
                    </div>
                    </div>
                </div>
            </div>
        </div>
        <ag-grid></ag-grid>
    </div>
    <modaltagadd></modaltagadd>
    <modaltagremove></modaltagremove>
</div>   
</template>

<script>
import AgGrid from './AgGrid.vue';
import ModalAddTags from './ModalAddTags.vue';
import ModalRemoveTags from './ModalRemoveTags.vue';

export default {
    props: [
        'tags',
        'tagsimg',
        'chainflt',
        'instanceAutocomplete',
        'documents'
    ],
    async created(){
        this.$store.commit('documentslist/setChainFilter', this.chainflt);
        this.$store.commit('documentslist/setDocTags', this.tags);
        this.$store.commit('documentslist/setPartsTags', this.tagsimg);
        await this.$store.dispatch('documentslist/getFilteredDocuments');
    },
    mounted: function () {
        $('#multiple-checkboxes').multiselect({
            includeSelectAllOption: true
        });
    },
    components: {
        'modaltagadd': ModalAddTags,
        'modaltagremove': ModalRemoveTags,
        'ag-grid': AgGrid,
    },
    computed: {
        doctagscid() {
            return this.$store.state.documentslist.tags;
        },
        parttagscid() {
            return this.$store.state.documentslist.tagsimg;
        },
    },
    methods: {
        IsNullOrEmptyOrUdf(s){
            if ((s != "") && (s != " ") && (s != null) && (typeof s !== 'undefined')) return true;
            else return false;
        },
        animatefunction(idd){
            $('#info-' + idd).slideToggle(300);
            $('#' + idd).toggleClass("rotate");
        },
        getTabFilters(value){
            let tab = [];
            $.each($("input[name='" + value + "']:checked"), function(){
                tab.push($(this).attr('id'));
            });
            return tab;
        },
        getFilterDocument(){
            //let chainfilter = getTabFilters('categorytag-D').join(',') + '¤' + getTabFilters('categorytag-P').join(',');
            let chainfilter = this.getTabFilters('categorytag-D').join(',');
            let baseUrlDoc = '/documents/';
            if(this.IsNullOrEmptyOrUdf(chainfilter)){
                let url = baseUrlDoc + chainfilter + '/filter/';
                document.location.href = url;
            }
            else {
                document.location.href = baseUrlDoc;
            }
        },
        activateFields(tab, bool){
            tab.forEach(function(item){
                $('#'+item).attr('disabled', bool);
            });
        },
        toggleselect(bool){
            $.each($("input.filterdoc:checkbox"), function(){
                $(this).prop('checked', bool);
            });
            this.getFilterDocument();
        },
        parseliststr(idd){
            return (this.chainflt.toString().split(',').includes(idd.toString())) ? true : false;
        },
        definepriority(p){
            let priority;
            switch (parseInt(p)) {
                case 5:
                    priority = 'danger';
                    break;
                case 4:
                    priority = 'warning';
                    break;
                case 3:
                    priority = 'light';
                    break;
                case 2:
                    priority = 'secondary';
                    break;
                default:
                    priority = 'dark';
            }
            return priority;
        }
    },

}

</script>

<style scoped>

</style>