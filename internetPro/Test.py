from django.shortcuts import render


def test(request):
    if request.method == 'GET':
       print("ok")
    return render(request, '../static/main.html')