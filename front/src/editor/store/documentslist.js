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
    basehosturl: "",
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
        console.log('avant 1');
        state.status_request = status;
        console.log('après1');
    },
    setDocumentID (state, idd) {
        state.documentID = idd
    },
    setFormError (state, val) {
        state.field_errors = val
    },
    setDocuments (state, docs) {
        assign(state.documents, docs)
    },
    setBaseUrl (state, baseurl) {
        state.basehosturl = baseurl
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
    }
}

export default {
    namespaced: true,
    state: initialState(),
    mutations,
    actions
}