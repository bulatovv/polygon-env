#include <bits/stdc++.h>

using namespace std;
 
int main() {
    unsigned long long n;
    unsigned long long c;
    cin >> n;
    cin >> c;
    unsigned long long b = 1;
    while(n--) {
        b *= 10;
    }
    
    while(c % 5 == 0 && b % 5 == 0) {
        c /= 5;
        b /= 5;
    }
    
    while(c % 2 == 0 && b % 2 == 0) {
        c /= 2;
        b /= 2;
    }
    
    long long INF = 1'000'000;
    
    if (c < INF && b < INF && c > 0) {
        cout << "YES" << endl << c << " " << b;
    } else {
        cout << "NO";
    }
}