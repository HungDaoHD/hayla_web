(function () {
  window.calendaroffcanvas = new bootstrap.Offcanvas('#calendar-reservation-add_edit_event');
  const calendarmodal = new bootstrap.Modal('#calendar-reservation-modal');
  var calendevent = '';
  
  var date = new Date();
  var d = date.getDate();
  var m = date.getMonth();
  var y = date.getFullYear();

  function eventContentStartOnly(arg, opts = {listView: false, hour12: false }) {
    // format only the START time
    const startOnly = FullCalendar.formatDate(arg.event.start, {
      hour: '2-digit',
      minute: '2-digit',
      hour12: !!opts.hour12,   // false → 24h; true → 12h
    });

    const prop = arg.event.extendedProps || {};

    // if (opts.listView) {
    //   var font_size = 'f-14';
    // }
    // else {
    //   var font_size = 'f-12';
    // } 

    return {
      html: `
        <div class="fc-evt">
          <div class="fc-evt-title">
            <span><i class="ti ti-a-b"></i>${prop.name}</span>
          </div> 

          <div class="fc-evt-row">
            <span><i class="ti ti-users"></i>${prop.people}</span>
          </div>

          <div class="fc-evt-row">
            <span><i class="ti ti-info-square"></i>${prop.status}</span>
          </div>

        </div>`
    };
    
  }

  const statusColors = {
    Arrived:   { bg:'#3881efff', text:'#fff' },
    Booking:   { bg:'#ffbf00ff', text:'#fff' },
    Cancel: { bg:'#dc3545', text:'#fff' },
    Leaved:   { bg:'#848484ff', text:'#fff' },
    default: { bg:'#848484ff', text:'#fff' },
  };

  window.calendar_reservation = new FullCalendar.Calendar(document.getElementById('calendar-reservation'), {
    
    headerToolbar: {
      left: 'prev,next today',
      center: 'title',
      right: 'timeGridDay,dayGridMonth,listMonth' // timeGridWeek
    },
    
    themeSystem: 'bootstrap',
    initialDate: date,

    // per-view title formats
    views: {
      timeGridDay: {  // Day view → "Tue, Oct 14, 2025"
        buttonText: 'Day',
        titleFormat: { month: 'short', day: 'numeric', year: 'numeric' },
        eventContent: (arg) => eventContentStartOnly(arg, { listView: false, hour12: false }), // 24h
        eventDidMount(info) {
          const s = info.event.extendedProps.status;
          const { bg, text } = statusColors[s] || statusColors.default;
          info.el.style.backgroundColor = bg;
          info.el.style.borderColor = bg;
          info.el.style.color = text;
        }
      
      },
      dayGridMonth: { // Month view → "October 2025"
        buttonText: 'Month',
        titleFormat: { month: 'short', year: 'numeric' },
      },
      listMonth: { // List (month) → "October 2025"
        buttonText: "List",
        titleFormat: { month: 'short', year: 'numeric' },
        eventContent: (arg) => eventContentStartOnly(arg, { listView: true, hour12: false }) // 24h
      }
    },
    
    initialView: 'timeGridDay',
    slotLabelFormat: { hour: '2-digit', minute: '2-digit', hour12: false },
    eventTimeFormat: { hour: '2-digit', minute: '2-digit', hour12: false },
    slotDuration: '00:30:00',
    slotMinTime: '08:00:00',
    slotMaxTime: '23:00:00',
    businessHours: { daysOfWeek: [0,1,2,3,4,5,6], startTime: '08:00', endTime: '22:00' },
    
    slotEventOverlap: false,
    eventOverlap: false,

    navLinks: true,
    height: 'auto',
    droppable: false,
    selectable: false,
    selectMirror: false,
    editable: false,
    dayMaxEvents: true,
    handleWindowResize: true,

    // select: function (info) {
    //   var sdt = new Date(info.start);
    //   var edt = new Date(info.end);
    //   document.getElementById('pc-e-sdate').value = sdt.getFullYear() + '-' + getRound(sdt.getMonth() + 1) + '-' + getRound(sdt.getDate());
    //   document.getElementById('pc-e-edate').value = edt.getFullYear() + '-' + getRound(edt.getMonth() + 1) + '-' + getRound(edt.getDate());

    //   document.getElementById('pc-e-title').value = "";
    //   document.getElementById('pc-e-venue').value = "";
    //   document.getElementById('pc-e-description').value = "";
    //   document.getElementById('pc-e-type').value = "";
    //   document.getElementById('pc-e-btn-text').innerHTML = '<i class="align-text-bottom me-1 ti ti-calendar-plus"></i> Add';
    //   document.querySelector('#pc_event_add').setAttribute('data-pc-action', 'add');

    //   calendaroffcanvas.show();
    //   calendar_reservation.unselect();
    // },

    eventClick: function (info) {

      calendevent = info.event;
      
      var clickedevent = info.event;
      var prop = clickedevent.extendedProps;

      document.querySelector('.calendar-modal-title').innerHTML = prop.name;
      document.querySelector('.pc-event-people').innerHTML = prop.people;
      document.querySelector('.pc-event-venue').innerHTML = prop.venue;
      document.querySelector('.pc-event-date').innerHTML = dateformat(clickedevent.start);
      document.querySelector('.pc-event-time').innerHTML = [getTime(clickedevent.start), getTime(clickedevent.end)].join(' to ');
      document.querySelector('.pc-event-status').innerHTML = prop.status;
      document.querySelector('.pc-event-description').innerHTML = prop.desc;

      calendarmodal.show();
    },
    
  });

  calendar_reservation.render();
  
  document.addEventListener('DOMContentLoaded', function () {
    var calbtn = document.querySelectorAll('.fc-toolbar-chunk');
    for (var t = 0; t < calbtn.length; t++) {
      var c = calbtn[t];
      c.children[0].classList.remove('btn-group');
      c.children[0].classList.add('d-inline-flex');
    }
  });

  var pc_event_remove = document.querySelector('#pc_event_remove');
  if (pc_event_remove) {

    pc_event_remove.addEventListener('click', function () {
      
      calendarmodal.hide();

      const swalWithBootstrapButtons = Swal.mixin({
        customClass: {
          confirmButton: 'btn btn-light-success',
          cancelButton: 'btn btn-light-danger'
        },
        buttonsStyling: false
      });

      swalWithBootstrapButtons
        .fire({
          title: 'Are you sure?',
          text: 'you want to delete this event?',
          icon: 'warning',
          showCancelButton: true,
          confirmButtonText: 'Yes, delete it!',
          cancelButtonText: 'No, cancel!',
          reverseButtons: true
        })
        .then((result) => {
          if (result.isConfirmed) {
            calendevent.remove();
            // calendarmodal.hide();
            swalWithBootstrapButtons.fire('Deleted!', 'Your Event has been deleted.', 'success');
          } else if (result.dismiss === Swal.DismissReason.cancel) {
            swalWithBootstrapButtons.fire('Cancelled', 'Your Event data is safe.', 'error');
          }
        });
    });
  }

  // var pc_event_add = document.querySelector('#pc_event_add');
  // if (pc_event_add) {
  //   pc_event_add.addEventListener('click', function () {
  //     var day = true;
  //     var end = null;
  //     var e_date_start = document.getElementById('pc-e-sdate').value === null ? '' : document.getElementById('pc-e-sdate').value;
  //     var e_date_end = document.getElementById('pc-e-edate').value === null ? '' : document.getElementById('pc-e-edate').value;
  //     if (!e_date_end == '') {
  //       end = new Date(e_date_end);
  //     }
  //     calendar_reservation.addEvent({
  //       title: document.getElementById('pc-e-title').value,
  //       start: new Date(e_date_start),
  //       end: end,
  //       allDay: day,
  //       description: document.getElementById('pc-e-description').value,
  //       venue: document.getElementById('pc-e-venue').value,
  //       className: document.getElementById('pc-e-type').value
  //     });
  //     if (pc_event_add.getAttribute('data-pc-action') == 'add') {
  //       Swal.fire({
  //         customClass: {
  //           confirmButton: 'btn btn-light-primary'
  //         },
  //         buttonsStyling: false,
  //         icon: 'success',
  //         title: 'Success',
  //         text: 'Event added successfully'
  //       });
  //     } else {
  //       calendevent.remove();
  //       document.getElementById('pc-e-btn-text').innerHTML = '<i class="align-text-bottom me-1 ti ti-calendar-plus"></i> Add';
  //       document.querySelector('#pc_event_add').setAttribute('data-pc-action', 'add');
  //       Swal.fire({
  //         customClass: {
  //           confirmButton: 'btn btn-light-primary'
  //         },
  //         buttonsStyling: false,
  //         icon: 'success',
  //         title: 'Success',
  //         text: 'Event Updated successfully'
  //       });
  //     }
  //     calendaroffcanvas.hide();
  //   });
  // }

  var pc_event_edit = document.querySelector('#pc_event_edit');
  if (pc_event_edit) {
    pc_event_edit.addEventListener('click', function () {

      console.log(calendevent);

      // var e_title = calendevent.title === undefined ? '' : calendevent.title;
      // var e_desc = calendevent.extendedProps.description === undefined ? '' : calendevent.extendedProps.description;
      // var e_date_start = calendevent.start === null ? '' : dateformat(calendevent.start);
      // var e_date_end = calendevent.end === null ? '' : " <i class='text-sm'>to</i> " + dateformat(calendevent.end);
      // e_date_end = calendevent.end === null ? '' : e_date_end;
      // var e_venue = calendevent.extendedProps.description === undefined ? '' : calendevent.extendedProps.venue;
      // var e_type = calendevent.classNames[0] === undefined ? '' : calendevent.classNames[0];

      // document.getElementById('pc-e-title').value = e_title;
      // document.getElementById('pc-e-venue').value = e_venue;
      // document.getElementById('pc-e-description').value = e_desc;
      // document.getElementById('pc-e-type').value = e_type;
      // var sdt = new Date(e_date_start);
      // var edt = new Date(e_date_end);
      // document.getElementById('pc-e-sdate').value = sdt.getFullYear() + '-' + getRound(sdt.getMonth() + 1) + '-' + getRound(sdt.getDate());
      // document.getElementById('pc-e-edate').value = edt.getFullYear() + '-' + getRound(edt.getMonth() + 1) + '-' + getRound(edt.getDate());
      // document.getElementById('pc-e-btn-text').innerHTML = '<i class="align-text-bottom me-1 ti ti-calendar-stats"></i> Update';
      // document.querySelector('#pc_event_add').setAttribute('data-pc-action', 'edit');
      
      calendarmodal.hide();
      calendaroffcanvas.show();
    });
  }

  //  get round value
  function getRound(vale) {
    var tmp = '';
    if (vale < 10) {
      tmp = '0' + vale;
    } else {
      tmp = vale;
    }
    return tmp;
  }

  //  get time
  function getTime(temp) {
    temp = new Date(temp);
    if (temp.getHours() != null) {
      var hour = temp.getHours();
      var minute = temp.getMinutes() ? temp.getMinutes() : '00';
      return hour + ':' + minute;
    }
  }

  //  get date
  function dateformat(dt) {
    var mn = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    
    var d = new Date(dt),
      month = '' + mn[d.getMonth()],
      day = '' + d.getDate(),
      year = d.getFullYear();

    if (month.length < 2) month = '0' + month;
    if (day.length < 2) day = '0' + day;
    
    // return [day + ' ' + month, year].join(',');

    return [month, day].join(', ');
  }

  //  get full date
  function timeformat(time) {
    var temp = time.split(':');
    var hours = temp[0];
    var minutes = temp[1];
    var newformat = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12;
    hours = hours ? hours : 12;
    minutes = minutes < 10 ? '0' + minutes : minutes;
    return hours + ':' + minutes + ' ' + newformat;
  }
})();
