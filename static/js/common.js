$( document ).ready(function() {
	tag1 = $('#tag1').text();
	tag2 = $('#tag2').text();
	stateObj = {'tag1': tag1, 'tag2': tag2 }
	url = '../' + tag1 + '/' + tag2;
	console.log('tag1', tag1, 'tag2', tag2, 'url', url, 'stateObj', stateObj);
	history.pushState(stateObj, "page 2", url);
});
