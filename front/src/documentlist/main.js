import Vue from 'vue'
import Vuex from 'vuex'
import {AgGridVue} from "ag-grid-vue"
import DocumentList from '../../vue/components/DocumentList.vue';

export var partVM = new Vue({
    el: "#appdoc",
    components: {
        'documentmanage': DocumentList,
    }
});