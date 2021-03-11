import { assign } from 'lodash'
import * as api from '../api'

export const initialState = () => ({
    tags: [],
    tagsimg: [],
    maptags: [],
    customstagsrmv: [],
    chainflt: "",
    status_request: 0,
    documentID: 0,
    field_errors: '',
    documents: [],
    multiselectvalues: []
})

export const mutations = {
    setDocTags (state, tags) {
        let mt = tags.map( function(tag) {
            let mp = {"label": tag.name, "value": tag.pk, "priority": tag.priority}
            return mp;
        });
        state.tags = mt;
    },
    setPartsTags (state, tags) {
        let mt = tags.map( function(tag) {
            let mp = {"label": tag.name, "value": tag.pk, "priority": tag.priority}
            return mp;
        });
        state.tagsimg = mt;
    },
    setUnlinkedTags (state, tags) {
        state.maptags = tags;
    },
    setCustomTagsrm (state, tags) {
        state.customstagsrmv = tags;
    },
    setChainFilter (state, chain) {
        state.chainflt = chain
    },
    setStatusRequest (state, status) {
        state.status_request = status;
    },
    setDocumentID (state, idd) {
        state.documentID = idd
    },
    setFormError (state, val) {
        state.field_errors = val
    },
    setDocuments (state, docs) {
        state.documents = docs
    },
    setMultiselected (state, selected) {
        state.multiselectvalues = selected
    },
}

export const actions = {
    async getunlinktagbydocument ({state, commit}, idd) {
        commit('setStatusRequest', 0);
        const resp = await api.retriveUnlinkTagByDocument({document: idd});
        commit('setUnlinkedTags', resp.data.tags);
        commit('setStatusRequest', resp.data.status);
    },
    async gettagbydocumentrm ({state, commit}, idd) {
        commit('setStatusRequest', 0);
        const resp = await api.retriveTagByDocument({document: idd});
        commit('setCustomTagsrm', resp.data.result);
        commit('setStatusRequest', resp.data.status);
    },
    async unassigntags ({state, commit}, data) {
        commit('setStatusRequest', 0);
        const resp = await api.unassignTagOnDocument(data);
        commit('setStatusRequest', resp.data.status);
    },
    async assigntags ({state, commit}, data) {
        commit('setStatusRequest', 0);
        const resp = await api.assignTagOnDocument(data);
        if((resp.data.action == 'add') && (resp.data.status == 200)) {
            state.tags.push(resp.data.result);
        }
        commit('setStatusRequest', resp.data.status);
    },
    async getFilteredDocuments ({state, commit}) {
        commit('setStatusRequest', 0);
        const resp = await api.getDocumentsByTags({chain: state.chainflt});
        if(resp.data.documents.length > 0) commit('setDocuments', resp.data.documents);
        commit('setStatusRequest', resp.status);
    }
}

export default {
    namespaced: true,
    state: initialState(),
    mutations,
    actions
}