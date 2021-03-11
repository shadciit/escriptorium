<template>
    <a v-bind:name="value" title="Assign tag" class="btn set-tag-meta btn-primary" data-toggle="modal" data-target="#tagAssignModal" v-on:click="launchmodal(value)">
        <i class="fas fa fa-tags"></i>
    </a>
</template>

<script>
    export default {
        name: 'Assigntg',
        data() {
            return {
                value: null
            }
        },
        beforeMount() {
            this.value = this.params.value;
        },
        methods: {
            async launchmodal(idd){
              this.$store.commit('documentslist/setDocumentID', idd);
              await this.$store.dispatch('documentslist/getunlinktagbydocument', idd);
            }
        }
    }
</script>

<style scoped>
</style>