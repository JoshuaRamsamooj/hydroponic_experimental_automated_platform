// warning flask box ========================================
function flashMessage(message, type, delay) {

    var html = '<div class="alert alert-'+type+'"> \
    <a href="#" class="close" data-dismiss="alert" aria-label="close"> \
    &times; \
    </a><strong>'+message+'</strong></div>'

    $(html).hide().appendTo("#flashMessage").fadeIn("slow", function(){
        $(this).delay(delay).fadeOut("slow");
    });
}


$(document).ready(function() {
    // errror handling 

    // tab activator for alarms==========================================
    var url = window.location;
    nav = url.pathname.split('/')[1]
    if (nav == 'alarms'){
        $('#alarmnav').addClass('active');
    }
    else if (nav == 'data'){
        $('#datanav').addClass('active');
    }
    else {

    $('ul.nav a').filter(function() {
        return this.href == url;
    }).parent().addClass('active');
    
    }

    // alarms =================================================
    // using SSE

    var numberOfAlarms
    $('#numberOfAlarms').text(numberOfAlarms)

    var alarmCountSource = new EventSource("/_count_alarms");
    
    alarmCountSource.onmessage = function(e) {
      $('#numberOfAlarms').text(e.data);
    }

    var alarmGetSource = new EventSource("/_get_alarms");
    
    alarmGetSource.onmessage = function(e) {
        
        if (e.data == 'True'){

            $('#alarmNotification').html('<div class="alert alert-info" role="alert" id="newAlarmAlert"> \
                <strong>New Alarm - </strong>Click <a href="/alarms/currentalarms/"><strong>here</strong></a> to view. \
                </div>');
    }
    }


    // update modal showing alarm id
    $("#comfirmAlarmClear").on('show.bs.modal', function(event){
        var alarm = $(event.relatedTarget) // alarm that triggered the modal
        var id = alarm.data('id') // Extract info from data-* attributes
        $('#alarmID', this).text(id);
        $('.alarmClear' , this).data('alarmID', id)
    });

    // clear alarm
    $("#comfirmAlarmClear").on('click', '.alarmClear', function(event){

        var id = $(this).data('alarmID')
        $.ajax({
            data: {
                alarmid: id
            },
            type: 'POST',
            url: '/_clear_alarm',
            success: function(data){
                // close modal and clear alarm from screen
                if (data.status == true){

                    $("#comfirmAlarmClear").modal('hide');
                    $("#"+id).alert('close');
                    console.log(id+' cleared')
                }
                else{
                    $("#comfirmAlarmClear").modal('hide');
                    $("#"+id).alert('close');
                    console.log('failed')
                }
            }
        });
    });
});
