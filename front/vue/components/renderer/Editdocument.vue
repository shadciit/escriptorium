<template>
    <a v-bind:href="'/document/'+ value +'/edit'" class="table-edit btn btn-info" v-bind:data-id="value" title="Edit document">
        <i class="fas fa-edit"></i>
    </a>
</template>

<script>
    export default {
        name: 'Editdocument',
        data() {
            return {
                value: null
            }
        },
        beforeMount() {
            this.value = this.params.value;
        }
    }
</script>

<style scoped>
</style>