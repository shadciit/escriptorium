import Vue from 'vue'
import store from '../editor/index';
import DocumentList from '../../vue/components/DocumentList.vue';
export var partVM = new Vue({
    el: "#appdoc",
    store,
    components: {
        'documentmanage': DocumentList,
    }
});