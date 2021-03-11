<template>
    <a v-bind:name="value" title="Remove tag" class="btn remove-tag-meta btn-danger" v-on:click="launchmodalunassign(value)">
        <i class="fas fa fa-tag"></i>
    </a>
</template>

<script>
    export default {
        name: 'Unassigntg',
        data() {
            return {
                value: null
            }
        },
        beforeMount() {
            this.value = this.params.value;
        },
        methods: {
            async launchmodalunassign(idd){
                $('#multiple-checkboxes').multiselect('destroy');
                this.$store.commit('documentslist/setDocumentID', idd);
                await this.$store.dispatch('documentslist/gettagbydocumentrm', this.$store.state.documentslist.documentID);
                setTimeout(() => {
                    $('#multiple-checkboxes').multiselect({
                        includeSelectAllOption: true,
                        onChange: function(element, checked) {
                        let brands = $('#multiple-checkboxes option:selected');
                        let selected = [];
                        $(brands).each(function(index, brand){
                            selected.push([$(this).val()]);
                        });
                        $('#selectedtags').val(selected.join(','));
                        }
                    });
                    $("#tagRemoveModal").modal('show');
                }, 1000);
            }
        }
    }
</script>

<style scoped>
</style>