export function bootModels() {
    let $alertsContainer = $('#alerts-container');

    let max_accuracy = {};

    $('#models-table tr.model-head').each(function(i, e) {
        max_accuracy[$(e).data('id')] = $('td#accuracy-'+$(e).data('id'), e).data('value');
    });

    $alertsContainer.on('training:start', function(ev, data) {
        let $row = $('tr#tr-'+data.id);
        $('.training-ongoing', $row).show();
        $('.training-done', $row).hide();
        $('.training-error', $row).hide();
        $('.cancel-training', $row).show();
    });
    $alertsContainer.on('training:gathering', function(ev, data) {
        let $row = $('tr#tr-'+data.id);
        $('.training-ongoing', $row).show();
        $('.training-done', $row).hide();
        $('.training-error', $row).hide();
        $('.training-gathering', $row).css('display', 'flex');
        $('.training-gathering .progress-bar', $row).css('width', Math.round(data.index/data.total*100)+'%');
        $('.cancel-training', $row).show();
    });
    $alertsContainer.on('training:eval', function(ev, data) {
        let $row = $('tr#tr-'+data.id);
        $('.training-ongoing', $row).show();
        $('.training-done', $row).hide();
        $('.training-error', $row).hide();
        $('.training-gathering', $row).hide();
        if (max_accuracy[data.id] < data.accuracy) {
            $row.data('value', data.accuracy);
            $('td#accuracy-'+data.id, $row).text(Math.round(data.accuracy*100*100)/100 + '%');
            max_accuracy[data.id] = data.accuracy;
        }
        $('.cancel-training', $row).show();
    });
    $alertsContainer.on('training:done', function(ev, data) {
        let $row = $('tr#tr-'+data.id);
        $('.training-ongoing', $row).hide();
        $('.training-done', $row).show();
        // $('.training-error', $row).hide();
        $('.training-gathering', $row).hide();
        $('.cancel-training', $row).hide();
        $('.cancel-training', $row).hide();
        $('.delete-model', $row).show();
        $('.job-is-finished', $row).html('<p>'+data.is_finished+'</p>');
        $('.accuracy', $row).html('<p>'+data.accuracy+'</p>');
    });
    $alertsContainer.on('training:error', function(ev, data) {
        let $row = $('tr#tr-'+data.id);
        $('.training-ongoing', $row).hide();
        $('.training-done', $row).hide();
        $('.training-error', $row).show();
        $('.cancel-training', $row).hide();
    });

    $alertsContainer.on('training:statechange', function(ev, data) {
        let $row = $('tr#tr-'+data.id);
        // $('#job-state').html(data["state"]);
        if(data.state == "PENDING"){
            $('.job-state', $row).html('<p style="color:blue">PENDING</p>');
        }else if(data.state == "RUNNING"){
            $('.job-state', $row).html('<p style="color:green">RUNNING</p>');
        }else if(data.state == "CANCELLED" || data.state == "OUT_OF_MEMORY" || data.state == "TIMEOUT"){
            $('.job-state', $row).html('<p style="color:red">'+data.state+'</p>');
        }else{
            $('.job-state', $row).html('<p>'+data.state+'</p>');
        }
        $('.job-is-finished', $row).html('<p>'+data.is_finished+'</p>');
    });


    $alertsContainer.on('training:senddone', function(ev, data) {
        let $row = $('tr#tr-'+data.id);
        // $('#job-state').html(data["state"]);
        if(data.state == "PENDING"){
            $('.job-state', $row).html('<p style="color:blue">PENDING</p>');
        }else if(data.state == "RUNNING"){
            $('.job-state', $row).html('<p style="color:green">RUNNING</p>');
        }else if(data.state == "CANCELLED" || data.state == "OUT_OF_MEMORY" || data.state == "TIMEOUT"){
            $('.job-state', $row).html('<p style="color:red">'+data.state+'</p>');
        }else{
            $('.job-state', $row).html('<p>'+data.state+'</p>');
        }

        $('.job-id', $row).html('<p>'+data.jobid+'</p>');

        $('.job-uuid', $row).html('<p>'+data.jobuuid+'</p>');

    });
}
