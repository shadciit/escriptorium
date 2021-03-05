import Vue from 'vue'
import {AgGridVue} from "ag-grid-vue"
import SelectPure from "select-pure"

import store from '../editor/index';
import DocumentList from '../../vue/components/DocumentList.vue';

export var partVM = new Vue({
    el: "#appdoc",
    store,
    components: {
        'documentmanage': DocumentList,
    }
});