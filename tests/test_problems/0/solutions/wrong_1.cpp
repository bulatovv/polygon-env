#include <bits/stdc++.h>

using namespace std;
 
int main() {
    long long n;
    long long c;
    cin >> n;
    cin >> c;
    int b = 1;
    while(n--) {
        b *= 10;
    }
    
    long long g = gcd(c, b);
    c /= g;
    b /= g;
    
    long long INF = 1'000'000;
    
    if (c < INF && b < INF) {
        cout << "YES" << endl <<  c << " " << b;
    } else {
        cout << "NO";
    }
}