document.addEventListener('DOMContentLoaded', function() {
    var avatar = document.getElementById('avatar-btn');
    var dropdown = document.getElementById('user-dropdown');
    if(avatar && dropdown){
        avatar.onclick = function(e){
            e.stopPropagation();
            dropdown.style.display = dropdown.style.display === 'block' ? 'none' : 'block';
        };
        document.addEventListener('click', function(){
            dropdown.style.display = 'none';
        });
    }
});