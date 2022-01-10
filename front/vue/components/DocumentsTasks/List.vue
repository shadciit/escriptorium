<template>
    <div>
        TEST
        {{ $store.state.documentsTasks }}
    </div>
</template>

<script>

export default {
    async created() {
        await this.$store.dispatch('fetchDocumentsTasks');
    },
}
</script>

<style scoped>
</style>